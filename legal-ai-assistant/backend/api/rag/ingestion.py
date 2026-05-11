# api/rag/ingestion.py
import os
from typing import List, Dict, Optional
import logging
from django.db import transaction
import PyPDF2

from ..models import Document, Chunk
from .chunker import HierarchicalChunker
from .embeddings import embedding_service
from .chroma_store import get_vector_store

logger = logging.getLogger(__name__)


class IngestionService:
    """Ingest documents: hierarchical chunk → embed → index in ChromaDB"""

    def __init__(self):
        self.chunker = HierarchicalChunker(chunk_size=800, chunk_overlap=150)
        self.embedding_service = embedding_service
        self.vector_store = get_vector_store()

    @transaction.atomic
    def ingest_document(self, document: Document, reindex: bool = False) -> Dict:
        try:
            existing = Chunk.objects.filter(document=document).count()
            if existing > 0 and not reindex:
                logger.info(f"Document {document.id} already indexed ({existing} chunks)")
                return {"success": True, "message": "Already indexed", "chunks": existing}

            if reindex:
                Chunk.objects.filter(document=document).delete()
                self.vector_store.delete_by_document(document.id)

            text = self._extract_text(document)
            if not text or len(text.strip()) < 100:
                raise ValueError("Document text too short or empty")

            base_meta = {
                "document_id": document.id,
                "title": document.title,
                "doctype": document.doctype,
                "jurisdiction": document.jurisdiction or "",
                "year": document.date.year if document.date else 0,
                "source": document.source or "",
            }

            chunks_data = self.chunker.chunk_text(
                text=text,
                document_title=document.title,
                metadata=base_meta,
            )
            logger.info(f"Created {len(chunks_data)} chunks for document {document.id}")

            chunk_texts = [c["text"] for c in chunks_data]
            embeddings = self.embedding_service.encode(chunk_texts, batch_size=32)
            logger.info(f"Generated {len(embeddings)} embeddings")

            # Save chunks to Django ORM
            chunk_objects = []
            for chunk_data, emb in zip(chunks_data, embeddings):
                chunk_objects.append(Chunk(
                    document=document,
                    ord=chunk_data["ord"],
                    heading=chunk_data.get("heading", ""),
                    text=chunk_data["text"],
                    embedding_json=emb.tolist(),
                ))
            Chunk.objects.bulk_create(chunk_objects)
            logger.info(f"Saved {len(chunk_objects)} chunks to DB")

            # Index into ChromaDB
            ids, texts, emb_lists, metas = [], [], [], []
            for chunk_data, chunk_obj, emb in zip(chunks_data, chunk_objects, embeddings):
                meta = base_meta.copy()
                meta.update({
                    "chunk_id": chunk_obj.id,
                    "heading": chunk_data.get("heading", ""),
                    "section_path": chunk_data.get("section_path", ""),
                    "ord": chunk_data["ord"],
                    "node_type": chunk_data.get("node_type", "text"),
                })
                ids.append(f"chunk_{chunk_obj.id}")
                texts.append(chunk_data["text"])
                emb_lists.append(emb.tolist())
                metas.append(meta)

            self.vector_store.add_chunks(ids, texts, emb_lists, metas)
            logger.info(f"Indexed {len(ids)} chunks in ChromaDB")

            return {
                "success": True,
                "document_id": document.id,
                "chunks_created": len(chunk_objects),
                "text_length": len(text),
            }

        except Exception as e:
            logger.error(f"Ingestion error for doc {document.id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _extract_text(self, document: Document) -> str:
        ext = os.path.splitext(document.path)[1].lower()
        if ext in (".txt", ".md"):
            with open(document.path, "r", encoding="utf-8") as f:
                return f.read()
        elif ext == ".pdf":
            text = ""
            with open(document.path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def ingest_multiple(self, documents: List[Document], reindex: bool = False) -> Dict:
        results = [self.ingest_document(doc, reindex) for doc in documents]
        successful = sum(1 for r in results if r.get("success"))
        total_chunks = sum(r.get("chunks_created", 0) for r in results)
        return {
            "total_documents": len(documents),
            "successful": successful,
            "failed": len(documents) - successful,
            "total_chunks": total_chunks,
            "results": results,
        }


ingestion_service = IngestionService()
