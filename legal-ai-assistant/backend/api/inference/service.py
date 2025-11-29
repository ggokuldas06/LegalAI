# api/inference/service.py
import time
import logging
from typing import Dict, Any, Optional, Iterator
from django.conf import settings

from .llm_engine import llm_engine
from .prompts import PromptBuilder
from .post_processor import ResponseProcessor

logger = logging.getLogger(__name__)


class InferenceService:
    """High-level service for LLM inference"""
    
    def __init__(self):
        self.engine = llm_engine
        self.processor = ResponseProcessor()
    
    def chat(
        self,
        mode: str,
        message: str,
        document_text: Optional[str] = None,
        document_title: Optional[str] = None,
        context_passages: Optional[list] = None,
        filters: Optional[Dict] = None,
        settings_override: Optional[Dict] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """
        Process chat request
        
        Args:
            mode: 'A', 'B', or 'C'
            message: User message
            document_text: Document text for modes A/B
            document_title: Document title
            context_passages: Retrieved passages for mode C
            filters: Filters for mode C
            settings_override: Custom inference settings
            stream: Whether to stream response
        
        Returns:
            Dict with response and metadata
        """
        start_time = time.time()
        
        try:
            # Build prompt
            prompt_kwargs = {'mode': mode}
            
            if mode == 'A':
                if not document_text:
                    raise ValueError("document_text required for mode A")
                prompt_kwargs.update({
                    'document_text': document_text,
                    'document_title': document_title or 'Untitled',
                })
            
            elif mode == 'B':
                if not document_text:
                    raise ValueError("document_text required for mode B")
                prompt_kwargs.update({
                    'document_text': document_text,
                    'document_title': document_title or 'Untitled',
                })
            
            elif mode == 'C':
                prompt_kwargs.update({
                    'question': message,
                    'context_passages': context_passages or [],
                })
            
            prompt = PromptBuilder.build_prompt(**prompt_kwargs)
            
            # Get inference settings
            model_config = settings.MODEL_CONFIG.copy()
            if settings_override:
                model_config.update(settings_override)
            
            # Count input tokens
            tokens_in = self.engine.count_tokens(prompt)
            
            # Generate response
            if stream:
                return self._stream_response(
                    prompt=prompt,
                    mode=mode,
                    tokens_in=tokens_in,
                    **model_config
                )
            else:
                response = self.engine.generate(
                    prompt=prompt,
                    max_tokens=model_config.get('max_tokens', 256),
                    temperature=model_config.get('temperature', 0.7),
                    top_p=model_config.get('top_p', 0.9),
                    top_k=model_config.get('top_k', 50),
                )
                
                # Process response
                processed = self._process_response(mode, response['text'])
                
                # Add disclaimer
                if processed.get('success'):
                    final_text = self.processor.add_disclaimer(response['text'])
                else:
                    final_text = response['text']
                
                latency_ms = int((time.time() - start_time) * 1000)
                
                return {
                    'success': True,
                    'mode': mode,
                    'response': final_text,
                    'processed': processed,
                    'tokens_in': tokens_in,
                    'tokens_out': response['tokens_generated'],
                    'latency_ms': latency_ms,
                    'finish_reason': response['finish_reason'],
                }
                
        except Exception as e:
            logger.error(f"Inference error: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'mode': mode,
                'latency_ms': int((time.time() - start_time) * 1000),
            }
    
    def _stream_response(
        self,
        prompt: str,
        mode: str,
        tokens_in: int,
        **kwargs
    ) -> Iterator[Dict[str, Any]]:
        """Stream response token by token"""
        try:
            # Send initial metadata
            yield {
                'type': 'start',
                'mode': mode,
                'tokens_in': tokens_in,
            }
            
            # Stream tokens
            for token in self.engine.generate_stream(prompt=prompt, **kwargs):
                yield {
                    'type': 'token',
                    'token': token,
                }
            
            # Send completion
            yield {
                'type': 'done',
                'disclaimer': self.processor.LEGAL_DISCLAIMER,
            }
            
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield {
                'type': 'error',
                'error': str(e),
            }
    
    def _process_response(self, mode: str, response_text: str) -> Dict[str, Any]:
        """Process response based on mode"""
        if mode == 'A':
            return self.processor.process_mode_a(response_text)
        elif mode == 'B':
            return self.processor.process_mode_b(response_text)
        elif mode == 'C':
            return self.processor.process_mode_c(response_text)
        else:
            return {'raw_response': response_text}
    
    def health_check(self) -> Dict[str, Any]:
        """Check if inference engine is ready"""
        return {
            'model_loaded': self.engine.is_loaded(),
            'model_path': settings.MODEL_CONFIG.get('model_path'),
        }


# Global instance
inference_service = InferenceService()