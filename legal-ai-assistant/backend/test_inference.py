# backend/test_inference.py
import os
import time
import json
import warnings
import django
from typing import Any, Dict, Optional

# --- Django setup ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

# Silence the llama.cpp duplicate BOS warning (cosmetic for tests)
warnings.filterwarnings(
    "ignore",
    message=r'Detected duplicate leading "<s>" in prompt.*',
    category=RuntimeWarning,
    module=r"llama_cpp\.llama",
)

from api.inference.service import inference_service  # noqa: E402


# ---------- helpers ----------
def _first_balanced_json_object(text: str) -> Optional[str]:
    """Return the first balanced {...} substring, or None."""
    if not text:
        return None
    s = text
    i = 0
    while True:
        start = s.find("{", i)
        if start == -1:
            return None
        depth = 0
        in_string = False
        esc = False
        for j in range(start, len(s)):
            ch = s[j]
            if in_string:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_string = False
                continue
            else:
                if ch == '"':
                    in_string = True
                    continue
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        return s[start : j + 1]
        # if we got here, this "{" never closed; look for the next "{"
        i = start + 1


def _extract_json_loose(text: str) -> Optional[Dict[str, Any]]:
    """Best-effort JSON extractor for mixed prose+JSON outputs."""
    if not text:
        return None
    # strip markdown code fences
    for fence in ("```json", "```"):
        text = text.replace(fence, "")
    text = text.replace("```", "")

    chunk = _first_balanced_json_object(text)
    if not chunk:
        return None

    # strict parse first
    try:
        return json.loads(chunk)
    except json.JSONDecodeError:
        pass

    # light repairs
    fixed = chunk
    # single quotes -> double
    fixed = fixed.replace("'", '"')
    # Python-isms -> JSON
    fixed = fixed.replace(": True", ": true").replace(": False", ": false").replace(": None", ": null")
    # strip trailing commas before } or ]
    fixed = fixed.replace(", }", " }").replace(",]", "]")

    try:
        return json.loads(fixed)
    except Exception:
        return None


def _preview(text: str, n: int = 220) -> str:
    return (text or "")[:n].replace("\n", " ") + ("..." if text and len(text) > n else "")


def _print_header(title: str):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def _run_mode_a(sample_contract: str):
    _print_header("Mode A — Summarizer")
    t0 = time.time()
    res = inference_service.chat(
        mode="A",
        message="Summarize this document. Respond ONLY with JSON as instructed by the system.",
        document_text=sample_contract,
        document_title="Employment Agreement",
    )
    dt = int((time.time() - t0) * 1000)

    print(f"Success: {res.get('success')}")
    print(f"Latency: {res.get('latency_ms', dt)} ms  |  Tokens In: {res.get('tokens_in', 0)}  |  Tokens Out: {res.get('tokens_out', 0)}")
    print("Raw preview:", _preview(res.get("response", "")))

    parsed = res.get("processed") or _extract_json_loose(res.get("response", ""))
    if isinstance(parsed, dict):
        print(f"Parsed JSON keys: {list(parsed.keys())[:10]}")
    else:
        print("Parsed JSON: None (model likely returned prose + JSON-ish text)")


def _run_mode_b(sample_contract: str):
    _print_header("Mode B — Clause Classifier")
    t0 = time.time()
    res = inference_service.chat(
        mode="B",
        message="Extract clauses. Respond ONLY with JSON.",
        document_text=sample_contract,
        document_title="Employment Agreement",
    )
    dt = int((time.time() - t0) * 1000)

    print(f"Success: {res.get('success')}")
    print(f"Latency: {res.get('latency_ms', dt)} ms")
    print("Raw preview:", _preview(res.get("response", "")))

    parsed = res.get("processed") or _extract_json_loose(res.get("response", ""))
    clauses = []
    if isinstance(parsed, dict):
        clauses = parsed.get("clauses") or parsed.get("items") or []
    print(f"Clauses Found: {len(clauses) if isinstance(clauses, list) else 0}")


def _run_mode_c():
    _print_header("Mode C — Case Law IRAC (no RAG)")
    t0 = time.time()
    res = inference_service.chat(
        mode="C",
        message="What is the standard for summary judgment? Respond ONLY with JSON.",
        context_passages=[
            {
                "case_name": "Anderson v. Liberty Lobby",
                "year": "1986",
                "text": "Summary judgment is appropriate when there is no genuine dispute as to any material fact.",
            }
        ],
    )
    dt = int((time.time() - t0) * 1000)

    print(f"Success: {res.get('success')}")
    print(f"Latency: {res.get('latency_ms', dt)} ms")
    print("Raw preview:", _preview(res.get("response", "")))

    parsed = res.get("processed") or _extract_json_loose(res.get("response", ""))
    citations = []
    if isinstance(parsed, dict):
        citations = parsed.get("citations") or []
    print(f"Citations Found: {len(citations) if isinstance(citations, list) else 0}")


def main():
    print("Testing LLM Inference Engine...\n")

    # Health check
    print("Health Check:")
    health = inference_service.health_check()
    print(f"  Model Loaded: {health.get('model_loaded')}")
    print(f"  Model Path:   {health.get('model_path')}")
    cfg = health.get("model_config") or {}
    if cfg:
        print(f"  n_ctx={cfg.get('n_ctx')}  n_threads={cfg.get('n_threads')}  n_gpu_layers={cfg.get('n_gpu_layers', 'N/A')}")

    # Sample doc for A/B
    sample_contract = """
    EMPLOYMENT AGREEMENT

    Section 1: Term
    This agreement shall commence on January 1, 2024 and continue for a period of two years.

    Section 2: Compensation
    Employee shall receive an annual salary of $120,000, payable in bi-weekly installments.

    Section 3: Termination
    Either party may terminate this agreement with 30 days written notice.
    """

    # Run modes
    _run_mode_a(sample_contract)
    _run_mode_b(sample_contract)
    _run_mode_c()

    print("\n✓ Inference testing complete!")


if __name__ == "__main__":
    main()
