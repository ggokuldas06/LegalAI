# api/inference/llm_engine.py
import os
import time
import logging
from typing import Dict, Any, Optional, Iterator
from llama_cpp import Llama

logger = logging.getLogger(__name__)


class LLMEngine:
    """Singleton LLM inference engine with lazy loading"""
    _instance = None
    _llm = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMEngine, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Don't load model in __init__ - wait for first use
        pass
    
    def _ensure_loaded(self):
        """Ensure model is loaded (lazy initialization)"""
        if not self._initialized:
            self.load_model()
            self._initialized = True
    
    def load_model(self):
        """Load the LLaMA model with llama-cpp-python"""
        if self._llm is not None:
            logger.info("Model already loaded")
            return
        
        try:
            # Import settings only when needed
            from django.conf import settings
            
            model_config = settings.MODEL_CONFIG
            model_path = model_config.get('model_path')
            
            if not model_path:
                raise ValueError("MODEL_PATH not configured in settings")
            
            if not os.path.exists(model_path):
                raise FileNotFoundError(
                    f"Model file not found at {model_path}. "
                    f"Please download the model first.\n"
                    f"You can download it from: "
                    f"https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF"
                )
            
            logger.info(f"Loading model from {model_path}...")
            start_time = time.time()
            
            self._llm = Llama(
                model_path=model_path,
                n_ctx=model_config.get('n_ctx', 4096),
                n_threads=model_config.get('n_threads', 8),
                n_gpu_layers=0,  # CPU only for M4 Mac
                verbose=False,
            )
            
            load_time = time.time() - start_time
            logger.info(f"Model loaded successfully in {load_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 256,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
        stop: Optional[list] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate text from prompt
        """
        # Ensure model is loaded before use
        self._ensure_loaded()
        
        if self._llm is None:
            raise RuntimeError("Model failed to load")
        
        try:
            start_time = time.time()
            
            response = self._llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                stop=stop or [],
                stream=stream,
                echo=False,
            )
            
            if stream:
                return response  # Return generator for streaming
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            return {
                'text': response['choices'][0]['text'],
                'tokens_generated': response['usage']['completion_tokens'],
                'tokens_prompt': response['usage']['prompt_tokens'],
                'latency_ms': latency_ms,
                'finish_reason': response['choices'][0]['finish_reason'],
            }
            
        except Exception as e:
            logger.error(f"Generation error: {e}")
            raise
    
    def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 256,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
        stop: Optional[list] = None,
        **kwargs
    ) -> Iterator[str]:
        """
        Stream generation token by token
        """
        # Ensure model is loaded before use
        self._ensure_loaded()
        
        if self._llm is None:
            raise RuntimeError("Model failed to load")
        
        try:
            stream = self._llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                stop=stop or [],
                stream=True,
                echo=False,
            )
            
            for chunk in stream:
                if 'choices' in chunk and len(chunk['choices']) > 0:
                    delta = chunk['choices'][0].get('text', '')
                    if delta:
                        yield delta
                        
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            raise
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        # Ensure model is loaded before use
        self._ensure_loaded()
        
        if self._llm is None:
            raise RuntimeError("Model failed to load")
        
        return len(self._llm.tokenize(text.encode('utf-8')))
    
    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self._llm is not None


# Create global instance (but don't load model yet)
llm_engine = LLMEngine()