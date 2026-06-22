# api/rag/ingestion.py
import os
from typing import List, Dict
import logging
from django.db import transaction

import fitz  # pymupdf

from ..models import Document, Chunk
from .chunker import HierarchicalChunker
from .embeddings import embedding_service
from .chroma_store import get_vector_store
from .vision_extractor import vision_extractor
from .doc_describer import doc_describer

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp", ".gif"}
TEXT_EXTENSIONS = {".txt", ".md"}
PDF_EXTENSION = ".pdf"

# Pages with fewer characters than this trigger vision OCR fallback
OCR_FALLBACK_THRESHOLD = 50


class IngestionService:
    """Ingest documents and images: extract → hierarchical chunk → embed → ChromaDB + BM25"""

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
            if not text or len(text.strip()) < 30:
                raise ValueError("Document text too short or empty after extraction")

            base_meta = {
                "document_id": document.id,
                "title": document.title,
                "doctype": document.doctype,
                "jurisdiction": document.jurisdiction or "",
                "year": document.date.year if document.date else 0,
                "source": document.source or "",
                "file_type": document.file_type,
            }

            chunks_data = self.chunker.chunk_text(
                text=text,
                document_title=document.title,
                metadata=base_meta,
            )
            logger.info(f"Created {len(chunks_data)} chunks for document {document.id}")

            chunk_texts = [c["text"] for c in chunks_data]
            embeddings = self.embedding_service.encode(chunk_texts, batch_size=32)

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
            logger.info(f"Indexed {len(ids)} chunks for document {document.id}")

            # Generate routing description (non-blocking — runs after index)
            self._generate_description(document, text)

            return {
                "success": True,
                "document_id": document.id,
                "chunks_created": len(chunk_objects),
                "text_length": len(text),
            }

        except Exception as e:
            logger.error(f"Ingestion error for doc {document.id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Text extraction
    # ------------------------------------------------------------------

    def _extract_text(self, document: Document) -> str:
        ext = os.path.splitext(document.path)[1].lower()

        if ext in TEXT_EXTENSIONS:
            document.file_type = "text"
            document.save(update_fields=["file_type"])
            with open(document.path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()

        elif ext == PDF_EXTENSION:
            return self._extract_pdf(document)

        elif ext in IMAGE_EXTENSIONS:
            return self._extract_image(document)

        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def _extract_pdf(self, document: Document) -> str:
        """Extract text from PDF using pymupdf with per-page OCR fallback for scanned pages."""
        doc = fitz.open(document.path)
        pages_text: List[str] = []
        ocr_pages = 0

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text").strip()

            if len(text) < OCR_FALLBACK_THRESHOLD:
                # Scanned page — use vision model
                logger.info(f"Page {page_num} of doc {document.id} sparse, using OCR fallback")
                text = vision_extractor.extract_from_pdf_page(document.path, page_num)
                ocr_pages += 1

            if text:
                pages_text.append(text)

        doc.close()
        page_count = len(pages_text)

        document.file_type = "pdf"
        document.page_count = page_count
        document.save(update_fields=["file_type", "page_count"])

        if ocr_pages:
            logger.info(f"Doc {document.id}: {ocr_pages}/{page_count} pages used OCR fallback")

        return "\n\n".join(pages_text)

    def _extract_image(self, document: Document) -> str:
        """Extract text/description from an image file via vision model."""
        document.file_type = "image"
        document.page_count = 1
        document.save(update_fields=["file_type", "page_count"])
        return vision_extractor.extract_from_image(document.path)

    # ------------------------------------------------------------------
    # Description generation
    # ------------------------------------------------------------------

    def _generate_description(self, document: Document, full_text: str):
        """Generate and store routing description. Runs after chunking, saves to DB."""
        try:
            description_json = doc_describer.generate_description(
                title=document.title,
                doctype=document.doctype,
                file_type=document.file_type,
                full_text=full_text,
            )
            document.doc_description = description_json
            document.save(update_fields=["doc_description"])
            logger.info(f"Description saved for document {document.id}")
        except Exception as e:
            logger.error(f"Description generation failed for doc {document.id}: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # Batch
    # ------------------------------------------------------------------

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
