# api/rag/ingestion.py
import os
from typing import List, Dict, Optional
import logging
from django.db import transaction
import PyPDF2

from ..models import Document, Chunk
from .chunker import DocumentChunker
from .embeddings import embedding_service
from .vector_store import get_vector_store

logger = logging.getLogger(__name__)


class IngestionService:
    """Service for ingesting documents into RAG system"""
    
    def __init__(self):
        self.chunker = DocumentChunker(chunk_size=500, chunk_overlap=100)
        self.embedding_service = embedding_service
        self.vector_store = get_vector_store()
    
    @transaction.atomic
    def ingest_document(
        self,
        document: Document,
        reindex: bool = False
    ) -> Dict:
        """
        Ingest a document: chunk, embed, and index
        
        Args:
            document: Document model instance
            reindex: Whether to reindex if already indexed
        
        Returns:
            Dict with ingestion statistics
        """
        try:
            # Check if already indexed
            existing_chunks = Chunk.objects.filter(document=document).count()
            if existing_chunks > 0 and not reindex:
                logger.info(f"Document {document.id} already indexed")
                return {
                    'success': True,
                    'message': 'Document already indexed',
                    'chunks': existing_chunks
                }
            
            # Delete existing chunks if reindexing
            if reindex:
                Chunk.objects.filter(document=document).delete()
            
            # Extract text
            text = self._extract_text(document)
            
            if not text or len(text.strip()) < 100:
                raise ValueError("Document text too short or empty")
            
            # Create metadata
            metadata = {
                'document_id': document.id,
                'title': document.title,
                'doctype': document.doctype,
                'jurisdiction': document.jurisdiction,
                'date': document.date,
                'year': document.date.year if document.date else None,
                'source': document.source,
            }
            
            # Chunk document
            chunks_data = self.chunker.chunk_text(
                text=text,
                document_title=document.title,
                metadata=metadata
            )
            
            logger.info(f"Created {len(chunks_data)} chunks for document {document.id}")
            
            # Generate embeddings in batches
            chunk_texts = [chunk['text'] for chunk in chunks_data]
            embeddings = self.embedding_service.encode(chunk_texts, batch_size=32)
            
            logger.info(f"Generated embeddings for {len(chunk_texts)} chunks")
            
            # Save chunks to database
            chunk_objects = []
            for i, (chunk_data, embedding) in enumerate(zip(chunks_data, embeddings)):
                chunk = Chunk(
                    document=document,
                    ord=chunk_data['ord'],
                    heading=chunk_data.get('heading', ''),
                    text=chunk_data['text'],
                    embedding_json=embedding.tolist()
                )
                chunk_objects.append(chunk)
            
            Chunk.objects.bulk_create(chunk_objects)
            
            logger.info(f"Saved {len(chunk_objects)} chunks to database")
            
            # Add to vector store
            vector_metadata = []
            for chunk_data, chunk_obj in zip(chunks_data, chunk_objects):
                meta = metadata.copy()
                meta.update({
                    'chunk_id': chunk_obj.id,
                    'text': chunk_data['text'],
                    'heading': chunk_data.get('heading', ''),
                    'ord': chunk_data['ord'],
                })
                vector_metadata.append(meta)
            
            self.vector_store.add_vectors(embeddings, vector_metadata)
            
            logger.info(f"Added {len(embeddings)} vectors to index")
            
            return {
                'success': True,
                'document_id': document.id,
                'chunks_created': len(chunk_objects),
                'embeddings_generated': len(embeddings),
                'text_length': len(text),
            }
            
        except Exception as e:
            logger.error(f"Ingestion error for document {document.id}: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_text(self, document: Document) -> str:
        """Extract text from document file"""
        file_ext = os.path.splitext(document.path)[1].lower()
        
        if file_ext == '.txt':
            with open(document.path, 'r', encoding='utf-8') as f:
                return f.read()
        
        elif file_ext == '.pdf':
            text = ""
            with open(document.path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text
        
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
    
    def ingest_multiple(
        self,
        documents: List[Document],
        reindex: bool = False
    ) -> Dict:
        """Ingest multiple documents"""
        results = []
        
        for document in documents:
            result = self.ingest_document(document, reindex=reindex)
            results.append(result)
        
        successful = sum(1 for r in results if r.get('success'))
        total_chunks = sum(r.get('chunks_created', 0) for r in results)
        
        return {
            'total_documents': len(documents),
            'successful': successful,
            'failed': len(documents) - successful,
            'total_chunks': total_chunks,
            'results': results,
        }


# Global instance
ingestion_service = IngestionService()