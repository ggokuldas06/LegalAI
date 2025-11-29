# api/rag/vector_store_numpy.py
import numpy as np
import pickle
import os
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class NumpyVectorStore:
    """NumPy-based vector store for similarity search (CPU-friendly)"""
    
    def __init__(self, embedding_dim: int = 384):
        """
        Args:
            embedding_dim: Dimension of embeddings
        """
        self.embedding_dim = embedding_dim
        self.vectors = None  # Will be numpy array
        self.metadata = []
        logger.info(f"Initialized NumPy vector store with dimension {embedding_dim}")
    
    def add_vectors(
        self,
        embeddings: np.ndarray,
        metadata: List[Dict]
    ):
        """
        Add vectors to the store
        
        Args:
            embeddings: numpy array of shape (n, embedding_dim)
            metadata: List of metadata dicts for each vector
        """
        if embeddings.shape[1] != self.embedding_dim:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.embedding_dim}, "
                f"got {embeddings.shape[1]}"
            )
        
        # Normalize vectors for cosine similarity
        embeddings = self._normalize(embeddings)
        
        # Add to store
        if self.vectors is None:
            self.vectors = embeddings
        else:
            self.vectors = np.vstack([self.vectors, embeddings])
        
        self.metadata.extend(metadata)
        
        logger.info(f"Added {len(embeddings)} vectors. Total: {self.size}")
    
    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 10,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search for similar vectors using cosine similarity
        
        Args:
            query_embedding: Query vector (1D array)
            k: Number of results to return
            filters: Optional filters to apply
        
        Returns:
            List of results with metadata and scores
        """
        if self.vectors is None or self.size == 0:
            logger.warning("Vector store is empty")
            return []
        
        # Ensure query is 1D
        if query_embedding.ndim == 2:
            query_embedding = query_embedding.squeeze()
        
        # Normalize query
        query_embedding = self._normalize(query_embedding.reshape(1, -1)).squeeze()
        
        # Compute cosine similarity (dot product of normalized vectors)
        similarities = np.dot(self.vectors, query_embedding)
        
        # Get top-k indices
        top_k = min(k * 2, len(similarities))  # Get extra for filtering
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        # Prepare results
        results = []
        for idx in top_indices:
            meta = self.metadata[idx].copy()
            
            # Apply filters
            if filters:
                if not self._matches_filters(meta, filters):
                    continue
            
            meta['score'] = float(similarities[idx])
            results.append(meta)
            
            if len(results) >= k:
                break
        
        return results
    
    def _normalize(self, vectors: np.ndarray) -> np.ndarray:
        """Normalize vectors to unit length"""
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        return vectors / norms
    
    def _matches_filters(self, metadata: Dict, filters: Dict) -> bool:
        """Check if metadata matches filters"""
        # Jurisdiction filter
        if 'jurisdiction' in filters and filters['jurisdiction']:
            doc_jurisdiction = metadata.get('jurisdiction', '')
            if doc_jurisdiction and doc_jurisdiction != filters['jurisdiction']:
                return False
        
        # Year range filter
        if 'year_from' in filters and filters['year_from']:
            doc_year = metadata.get('year')
            if doc_year and doc_year < filters['year_from']:
                return False
        
        if 'year_to' in filters and filters['year_to']:
            doc_year = metadata.get('year')
            if doc_year and doc_year > filters['year_to']:
                return False
        
        # Keyword include filter
        if 'include' in filters and filters['include']:
            text = metadata.get('text', '').lower()
            if not any(keyword.lower() in text for keyword in filters['include']):
                return False
        
        # Keyword exclude filter
        if 'exclude' in filters and filters['exclude']:
            text = metadata.get('text', '').lower()
            if any(keyword.lower() in text for keyword in filters['exclude']):
                return False
        
        return True
    
    def save(self, path: str):
        """Save store to disk"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        # Save as single pickle file
        data = {
            'vectors': self.vectors,
            'metadata': self.metadata,
            'embedding_dim': self.embedding_dim
        }
        
        with open(f"{path}.pkl", 'wb') as f:
            pickle.dump(data, f)
        
        logger.info(f"Saved vector store to {path}.pkl")
    
    def load(self, path: str):
        """Load store from disk"""
        with open(f"{path}.pkl", 'rb') as f:
            data = pickle.load(f)
        
        self.vectors = data['vectors']
        self.metadata = data['metadata']
        self.embedding_dim = data['embedding_dim']
        
        logger.info(
            f"Loaded vector store from {path}.pkl. "
            f"Total vectors: {self.size}"
        )
    
    def clear(self):
        """Clear the store"""
        self.vectors = None
        self.metadata = []
        logger.info("Cleared vector store")
    
    @property
    def size(self) -> int:
        """Get number of vectors in store"""
        return len(self.metadata) if self.metadata else 0


# Global instance (lazy initialization)
_global_vector_store = None

def get_vector_store() -> NumpyVectorStore:
    """Get or create global vector store"""
    global _global_vector_store
    
    if _global_vector_store is None:
        from .embeddings import embedding_service
        _global_vector_store = NumpyVectorStore(
            embedding_dim=embedding_service.embedding_dim
        )
    
    return _global_vector_store