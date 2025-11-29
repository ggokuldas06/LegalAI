# api/rag/embeddings.py
from sentence_transformers import SentenceTransformer
import numpy as np
import logging
from typing import List, Union
# import os for checking local path
import os 

logger = logging.getLogger(__name__)

LOCAL_MODEL_PATH = '/Users/gokuldasgirishkumar/code/legal_adivisor/legal-ai-assistant/backend/api/rag/local_models/all-MiniLM-L6-v2' 

class EmbeddingService:
    """Service for generating text embeddings"""
    
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._model is None:
            self.load_model()
    
    def load_model(self):
        """Load the sentence transformer model"""
        
        # 1. Determine the path to load from
        if os.path.exists(LOCAL_MODEL_PATH):
            model_path = LOCAL_MODEL_PATH
            logger.info(f"Loading embedding model from **LOCAL PATH**: {model_path}")
        else:
            # 2. Fallback or use original setting (Only use this line if temporary online access is okay)
            model_path = 'all-MiniLM-L6-v2' 
            logger.warning(f"Local model not found at {LOCAL_MODEL_PATH}. Attempting to load **ONLINE** from: {model_path}")
            
        try:
            # Load the model from the determined path/name
            self._model = SentenceTransformer(model_path)
            self._embedding_dim = 384
            
            logger.info(f"Embedding model loaded. Dimension: {self._embedding_dim}")
            
        except Exception as e:
            # Raise an informative error if it fails to load
            logger.error(f"Failed to load embedding model from {model_path}. Error: {e}")
            raise RuntimeError(f"FATAL: Failed to load required model from {model_path}. Ensure files are present.")
    
    def encode(self, texts: Union[str, List[str]], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for text(s)
        
        Args:
            texts: Single text or list of texts
            batch_size: Batch size for encoding
        
        Returns:
            numpy array of embeddings
        """
        if self._model is None:
            raise RuntimeError("Embedding model not loaded")
        
        # Convert single text to list
        if isinstance(texts, str):
            texts = [texts]
        
        try:
            embeddings = self._model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True
            )
            return embeddings
            
        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            raise
    
    def encode_single(self, text: str) -> np.ndarray:
        """Generate embedding for a single text"""
        return self.encode(text)[0]
    
    @property
    def embedding_dim(self) -> int:
        """Get embedding dimension"""
        return self._embedding_dim
    
    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self._model is not None


# Global instance
embedding_service = EmbeddingService()