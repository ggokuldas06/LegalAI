# api/rag/chroma_store.py
import os
import logging
import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

CHROMA_PATH = str(Path(__file__).resolve().parents[4] / "data" / "chroma_db")


def _tokenize(text: str) -> List[str]:
    """Simple whitespace tokenizer for BM25."""
    return text.lower().split()


class ChromaHybridStore:
    """
    ChromaDB-backed vector store with in-memory BM25 index.
    Retrieval uses Reciprocal Rank Fusion (RRF) to merge BM25 and vector scores.
    """

    COLLECTION_NAME = "legal_chunks"

    def __init__(self, persist_path: str = CHROMA_PATH):
        os.makedirs(persist_path, exist_ok=True)
        self._client = chromadb.PersistentClient(path=persist_path)
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        # BM25 state: parallel arrays with chunk ids
        self._bm25_ids: List[str] = []
        self._bm25_corpus: List[List[str]] = []
        self._bm25: Optional[BM25Okapi] = None

        self._rebuild_bm25()
        logger.info(
            f"ChromaHybridStore ready — {self._collection.count()} chunks in Chroma, "
            f"{len(self._bm25_ids)} in BM25"
        )

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def add_chunks(
        self,
        ids: List[str],
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict],
    ):
        """Add chunks to Chroma and update the BM25 index."""
        if not ids:
            return

        # Chroma requires metadata values to be str/int/float/bool
        safe_metas = [self._sanitize_meta(m) for m in metadatas]

        self._collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=safe_metas,
        )

        # Extend BM25 structures
        self._bm25_ids.extend(ids)
        self._bm25_corpus.extend([_tokenize(t) for t in texts])
        self._bm25 = BM25Okapi(self._bm25_corpus)

        logger.info(f"Added {len(ids)} chunks. Total: {self._collection.count()}")

    def delete_by_document(self, document_id: int):
        """Remove all chunks belonging to a document."""
        try:
            results = self._collection.get(
                where={"document_id": document_id},
                include=[],
            )
            ids_to_delete = results.get("ids", [])
            if ids_to_delete:
                self._collection.delete(ids=ids_to_delete)
                # Rebuild BM25 after deletion
                self._rebuild_bm25()
                logger.info(f"Deleted {len(ids_to_delete)} chunks for doc {document_id}")
        except Exception as e:
            logger.error(f"delete_by_document error: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # Hybrid search
    # ------------------------------------------------------------------

    def search(
        self,
        query_embedding: np.ndarray,
        query_text: str,
        k: int = 10,
        filters: Optional[Dict] = None,
        rrf_k: int = 60,
        vector_weight: float = 0.5,
    ) -> List[Dict]:
        """
        Hybrid BM25 + vector search with Reciprocal Rank Fusion.
        Returns up to k results sorted by fused RRF score (descending).
        """
        if self._collection.count() == 0:
            logger.warning("ChromaHybridStore is empty")
            return []

        candidate_k = min(k * 4, self._collection.count())

        # --- Vector search ---
        vector_ids = self._vector_search(query_embedding, candidate_k, filters)

        # --- BM25 search ---
        bm25_ids = self._bm25_search(query_text, candidate_k, filters)

        # --- RRF fusion ---
        fused = self._rrf(
            [bm25_ids, vector_ids],
            k=rrf_k,
        )

        # Fetch full metadata for top-k fused ids
        top_ids = [id_ for id_, _ in fused[:k]]
        if not top_ids:
            return []

        raw = self._collection.get(
            ids=top_ids,
            include=["documents", "metadatas"],
        )

        id_to_result: Dict[str, Dict] = {}
        for chunk_id, doc, meta in zip(raw["ids"], raw["documents"], raw["metadatas"]):
            id_to_result[chunk_id] = {**meta, "text": doc, "chunk_id": chunk_id}

        # Preserve fused rank order and attach score
        results = []
        id_to_score = {id_: score for id_, score in fused}
        for id_ in top_ids:
            if id_ in id_to_result:
                entry = id_to_result[id_].copy()
                entry["score"] = id_to_score.get(id_, 0.0)
                results.append(entry)

        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _vector_search(
        self,
        query_embedding: np.ndarray,
        k: int,
        filters: Optional[Dict],
    ) -> List[str]:
        """Returns ordered list of chunk ids from cosine vector search."""
        where = self._build_where(filters)
        kwargs = dict(
            query_embeddings=[query_embedding.tolist()],
            n_results=min(k, self._collection.count()),
            include=["metadatas"],
        )
        if where:
            kwargs["where"] = where
        try:
            results = self._collection.query(**kwargs)
            return results["ids"][0] if results["ids"] else []
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []

    def _bm25_search(
        self,
        query: str,
        k: int,
        filters: Optional[Dict],
    ) -> List[str]:
        """Returns ordered list of chunk ids from BM25 search."""
        if not self._bm25 or not self._bm25_ids:
            return []

        tokens = _tokenize(query)
        scores = self._bm25.get_scores(tokens)
        ranked_indices = np.argsort(scores)[::-1]

        # Apply metadata filters if needed (fetch filtered ids from Chroma first)
        filtered_ids: Optional[set] = None
        where = self._build_where(filters)
        if where:
            try:
                res = self._collection.get(where=where, include=[])
                filtered_ids = set(res.get("ids", []))
            except Exception:
                filtered_ids = None

        result_ids = []
        for idx in ranked_indices:
            if idx >= len(self._bm25_ids):
                continue
            chunk_id = self._bm25_ids[idx]
            if filtered_ids is not None and chunk_id not in filtered_ids:
                continue
            if scores[idx] > 0:
                result_ids.append(chunk_id)
            if len(result_ids) >= k:
                break

        return result_ids

    @staticmethod
    def _rrf(ranked_lists: List[List[str]], k: int = 60) -> List[Tuple[str, float]]:
        """Reciprocal Rank Fusion over multiple ranked lists of ids."""
        scores: Dict[str, float] = {}
        for ranked in ranked_lists:
            for rank, id_ in enumerate(ranked):
                scores[id_] = scores.get(id_, 0.0) + 1.0 / (k + rank + 1)
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    def _rebuild_bm25(self):
        """Rebuild BM25 index from all chunks currently in Chroma."""
        try:
            count = self._collection.count()
            if count == 0:
                self._bm25_ids = []
                self._bm25_corpus = []
                self._bm25 = None
                return

            # Fetch all chunks (Chroma has no pagination but handles moderate sizes fine)
            results = self._collection.get(include=["documents"])
            self._bm25_ids = results["ids"]
            self._bm25_corpus = [_tokenize(doc) for doc in results["documents"]]
            self._bm25 = BM25Okapi(self._bm25_corpus)
        except Exception as e:
            logger.error(f"BM25 rebuild error: {e}", exc_info=True)

    @staticmethod
    def _build_where(filters: Optional[Dict]) -> Optional[Dict]:
        """Convert frontend filters dict to Chroma where clause."""
        if not filters:
            return None

        conditions = []

        if filters.get("document_id"):
            conditions.append({"document_id": {"$eq": int(filters["document_id"])}})

        if filters.get("jurisdiction"):
            conditions.append({"jurisdiction": {"$eq": filters["jurisdiction"]}})

        if filters.get("year_from"):
            conditions.append({"year": {"$gte": int(filters["year_from"])}})

        if filters.get("year_to"):
            conditions.append({"year": {"$lte": int(filters["year_to"])}})

        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    @staticmethod
    def _sanitize_meta(meta: Dict) -> Dict:
        """Ensure all metadata values are Chroma-compatible types."""
        clean = {}
        for k, v in meta.items():
            if v is None:
                clean[k] = ""
            elif isinstance(v, (str, int, float, bool)):
                clean[k] = v
            else:
                clean[k] = str(v)
        return clean

    @property
    def size(self) -> int:
        return self._collection.count()


# Global singleton
_store: Optional[ChromaHybridStore] = None


def get_vector_store() -> ChromaHybridStore:
    global _store
    if _store is None:
        _store = ChromaHybridStore()
    return _store
