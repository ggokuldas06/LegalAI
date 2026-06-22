# api/rag/doc_describer.py
import json
import logging
import re
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
DESCRIPTION_MODEL = "gemma4:latest"

_SYSTEM = (
    "You are a legal document analyst. "
    "Given the title, type, and opening text of a document, produce a concise routing description. "
    "Output ONLY valid JSON — no markdown fences, no commentary."
)

_USER_TEMPLATE = """Title: {title}
Document type: {doctype}
File type: {file_type}

First 3000 characters of content:
{text_preview}

Output JSON exactly in this format:
{{
  "summary": "<2-3 sentence overview of what this document is>",
  "topics": ["<topic1>", "<topic2>", "<topic3>"],
  "parties": ["<party name or role>"],
  "jurisdiction": "<detected jurisdiction or empty string>",
  "key_sections": ["<section name>"],
  "document_type_detail": "<specific type e.g. employment contract, merger agreement, court ruling>"
}}"""


def _parse_json_from_response(text: str) -> Optional[dict]:
    """Extract JSON from LLM response, handling markdown fences."""
    text = text.strip()
    # Strip ```json ... ``` fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find a JSON object within the text
        match = re.search(r"\{[\s\S]+\}", text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return None


class DocDescriber:
    """
    Generates a structured routing description for a document using the local LLM.
    The description is stored as JSON in Document.doc_description and used by
    DocRouter to decide which documents to retrieve from at query time.
    """

    def generate_description(
        self,
        title: str,
        doctype: str,
        file_type: str,
        full_text: str,
    ) -> str:
        """
        Returns a JSON string with structured description.
        Falls back to a minimal JSON on failure.
        """
        text_preview = full_text[:3000] if full_text else "(no text extracted)"
        user_msg = _USER_TEMPLATE.format(
            title=title,
            doctype=doctype,
            file_type=file_type,
            text_preview=text_preview,
        )

        payload = {
            "model": DESCRIPTION_MODEL,
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            "stream": False,
            "options": {"num_predict": 1024, "temperature": 0.2},
        }

        try:
            with httpx.Client(timeout=120.0) as client:
                resp = client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
                resp.raise_for_status()
            raw = resp.json()["message"]["content"]
            parsed = _parse_json_from_response(raw)
            if parsed:
                logger.info(f"Description generated for '{title}'")
                return json.dumps(parsed)
            logger.warning(f"Could not parse description JSON for '{title}', using fallback")
        except Exception as e:
            logger.error(f"DocDescriber error for '{title}': {e}", exc_info=True)

        # Minimal fallback so routing still works
        fallback = {
            "summary": f"{doctype} document titled '{title}'.",
            "topics": [doctype],
            "parties": [],
            "jurisdiction": "",
            "key_sections": [],
            "document_type_detail": doctype,
        }
        return json.dumps(fallback)


doc_describer = DocDescriber()
