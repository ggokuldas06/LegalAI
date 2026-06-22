# api/rag/vision_extractor.py
import base64
import logging
import os
from pathlib import Path
from typing import Optional

import fitz  # pymupdf
import httpx

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
VISION_MODEL = "qwen2.5vl:7b"

VISION_PROMPT = (
    "You are a document extraction assistant. "
    "Examine this image carefully and do the following:\n"
    "1. If the image contains text (typed or handwritten), transcribe it fully and accurately.\n"
    "2. If the image contains a table, reproduce its structure and all data as plain text.\n"
    "3. If the image contains charts, diagrams, or figures, describe their content in detail.\n"
    "4. If the image contains signatures, stamps, or logos, note their presence.\n"
    "Output everything as plain text. Do not add commentary or explanations."
)


def _encode_image_file(path: str) -> str:
    """Return base64-encoded image data."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _encode_pixmap(pix: fitz.Pixmap) -> str:
    """Convert a pymupdf Pixmap to base64 PNG."""
    return base64.b64encode(pix.tobytes("png")).decode("utf-8")


def _call_vision(image_b64: str, timeout: float = 120.0) -> str:
    """Send a single image to the Ollama vision model and return extracted text."""
    payload = {
        "model": VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": VISION_PROMPT,
                "images": [image_b64],
            }
        ],
        "stream": False,
        "options": {"num_predict": 2048, "temperature": 0.1},
    }
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
        resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


class VisionExtractor:
    """
    Extract text from images and scanned PDF pages using a local vision model.
    Uses qwen2.5vl:7b via Ollama — no external API calls.
    """

    def extract_from_image(self, path: str) -> str:
        """Extract text/description from a standalone image file (PNG/JPG/etc.)."""
        try:
            b64 = _encode_image_file(path)
            result = _call_vision(b64)
            logger.info(f"Vision extraction for {Path(path).name}: {len(result)} chars")
            return result
        except Exception as e:
            logger.error(f"Vision extraction failed for {path}: {e}", exc_info=True)
            return ""

    def extract_from_pdf_page(self, pdf_path: str, page_num: int, dpi: int = 150) -> str:
        """
        Render a single PDF page to an image and extract its text via vision model.
        Used as OCR fallback for scanned / image-only PDF pages.
        """
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_num]
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            doc.close()
            b64 = _encode_pixmap(pix)
            result = _call_vision(b64, timeout=90.0)
            logger.debug(f"OCR fallback page {page_num}: {len(result)} chars")
            return result
        except Exception as e:
            logger.error(f"PDF page vision extraction failed (page {page_num}): {e}", exc_info=True)
            return ""


vision_extractor = VisionExtractor()
