# api/rag/vector_store.py
# Replace the entire file with a redirect to the NumPy version

from .vector_store_numpy import NumpyVectorStore as VectorStore
from .vector_store_numpy import get_vector_store

__all__ = ['VectorStore', 'get_vector_store']