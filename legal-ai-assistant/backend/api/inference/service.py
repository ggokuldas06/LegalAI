# api/inference/service.py
import time
import logging
from typing import Dict, Any, Optional, Iterator, List
from django.conf import settings

from .llm_engine import llm_engine
from .prompts import PromptBuilder, LEGAL_DISCLAIMER
from .post_processor import ResponseProcessor

logger = logging.getLogger(__name__)


class InferenceService:
    """High-level service for Ollama-backed LLM inference."""

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
    ) -> Any:
        start = time.time()
        try:
            # Build messages list for Ollama chat API
            kwargs: Dict = {"mode": mode}
            if mode == "A":
                if not document_text:
                    raise ValueError("document_text required for mode A")
                kwargs.update(
                    document_text=document_text,
                    document_title=document_title or "Untitled",
                )
            elif mode == "B":
                if not document_text:
                    raise ValueError("document_text required for mode B")
                kwargs.update(
                    document_text=document_text,
                    document_title=document_title or "Untitled",
                )
            elif mode == "C":
                kwargs.update(
                    question=message,
                    context_passages=context_passages or [],
                )

            messages = PromptBuilder.build_messages(**kwargs)

            # Merge inference settings
            model_config = settings.MODEL_CONFIG.copy()
            if settings_override:
                model_config.update(settings_override)

            gen_kwargs = {
                "max_tokens": model_config.get("max_tokens", 1024),
                "temperature": model_config.get("temperature", 0.7),
                "top_p": model_config.get("top_p", 0.9),
                "top_k": model_config.get("top_k", 50),
            }

            tokens_in = self.engine.count_tokens(
                " ".join(m["content"] for m in messages)
            )

            if stream:
                return self._stream_response(messages, mode, tokens_in, **gen_kwargs)

            response = self.engine.generate(messages=messages, **gen_kwargs)
            processed = self._process_response(mode, response["text"])
            final_text = response["text"] + LEGAL_DISCLAIMER
            latency_ms = int((time.time() - start) * 1000)

            return {
                "success": True,
                "mode": mode,
                "response": final_text,
                "processed": processed,
                "tokens_in": tokens_in,
                "tokens_out": response.get("tokens_generated", 0),
                "latency_ms": latency_ms,
                "finish_reason": response.get("finish_reason", "stop"),
            }

        except Exception as e:
            logger.error(f"Inference error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "mode": mode,
                "latency_ms": int((time.time() - start) * 1000),
            }

    def _stream_response(
        self,
        messages: List[Dict],
        mode: str,
        tokens_in: int,
        **gen_kwargs,
    ) -> Iterator[Dict[str, Any]]:
        try:
            yield {"type": "start", "mode": mode, "tokens_in": tokens_in}

            for token in self.engine.generate_stream(messages=messages, **gen_kwargs):
                yield {"type": "token", "token": token}

            yield {"type": "done", "disclaimer": LEGAL_DISCLAIMER}

        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield {"type": "error", "error": str(e)}

    def _process_response(self, mode: str, text: str) -> Dict:
        if mode == "A":
            return self.processor.process_mode_a(text)
        elif mode == "B":
            return self.processor.process_mode_b(text)
        elif mode == "C":
            return self.processor.process_mode_c(text)
        return {"raw_response": text}

    def health_check(self) -> Dict[str, Any]:
        return {
            "model_loaded": self.engine.is_loaded(),
            "model": self.engine.model,
            "ollama_url": self.engine.base_url,
        }


inference_service = InferenceService()
