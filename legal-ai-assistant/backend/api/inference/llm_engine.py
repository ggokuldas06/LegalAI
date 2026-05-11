# api/inference/llm_engine.py
import json
import logging
import re
import time
from typing import Iterator, List, Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "gemma4:latest"


class OllamaLLMEngine:
    """
    Ollama-backed LLM engine using gemma4:latest.

    gemma4 in Ollama 0.23.x has a known streaming issue when using the /api/chat
    endpoint with a system message — it returns empty content tokens. We work around
    this by fetching the full response non-streaming and then yielding word-by-word
    to give the frontend a progressive streaming experience.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.model = DEFAULT_MODEL

    # ------------------------------------------------------------------
    # Non-streaming generation
    # ------------------------------------------------------------------

    def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
        **kwargs,
    ) -> Dict[str, Any]:
        """Send a chat completion request and return the full response.

        Gemma 4 uses internal chain-of-thought tokens that count toward num_predict.
        For longer legal prompts, num_predict must be large enough (>= 1024) to allow
        both internal reasoning AND the visible response.  We enforce a safe minimum.
        """
        start = time.time()
        # Ensure num_predict is large enough for Gemma 4's thinking+response budget.
        safe_num_predict = max(max_tokens, 2048)
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": safe_num_predict,
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
            },
        }
        try:
            with httpx.Client(timeout=180.0) as client:
                resp = client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()

            text = data["message"]["content"]
            latency_ms = int((time.time() - start) * 1000)

            return {
                "text": text,
                "tokens_generated": data.get("eval_count", 0),
                "tokens_prompt": data.get("prompt_eval_count", 0),
                "latency_ms": latency_ms,
                "finish_reason": data.get("done_reason", "stop"),
            }
        except httpx.HTTPError as e:
            logger.error(f"Ollama HTTP error: {e}")
            raise RuntimeError(f"Ollama request failed: {e}") from e

    # ------------------------------------------------------------------
    # Streaming generation (simulated for gemma4 compatibility)
    # ------------------------------------------------------------------

    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
        **kwargs,
    ) -> Iterator[str]:
        """
        Stream tokens. Uses simulated streaming for gemma4 (full response then
        word-by-word delivery) due to Ollama 0.23.x streaming bug with system messages.
        """
        full = self.generate(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
        )
        text = full.get("text", "")
        yield from self._word_stream(text)

    @staticmethod
    def _word_stream(text: str) -> Iterator[str]:
        """
        Split text into natural streaming chunks (words + punctuation) so the
        frontend gets a typewriter effect.
        """
        # Split by whitespace but keep the delimiter for natural flow
        tokens = re.split(r'(\s+)', text)
        for tok in tokens:
            if tok:
                yield tok

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def count_tokens(self, text: str) -> int:
        """Approximate token count (4 chars ≈ 1 token for Gemma)."""
        return max(1, len(text) // 4)

    def is_loaded(self) -> bool:
        """Check if Ollama is reachable and the model is available."""
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    models = [m["name"] for m in resp.json().get("models", [])]
                    return any(self.model.split(":")[0] in m for m in models)
        except Exception:
            pass
        return False


# Global singleton
llm_engine = OllamaLLMEngine()
