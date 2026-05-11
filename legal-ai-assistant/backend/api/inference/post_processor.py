# api/inference/post_processor.py
import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

LEGAL_DISCLAIMER = (
    "\n\n---\n"
    "**DISCLAIMER:** This is informational analysis only and does not constitute "
    "legal advice. Consult a qualified attorney for legal guidance."
)


class ResponseProcessor:
    """Post-process Markdown LLM responses for each mode."""

    LEGAL_DISCLAIMER = LEGAL_DISCLAIMER

    @staticmethod
    def _extract_citations(text: str) -> List[str]:
        """Extract all [citation] references from text."""
        return re.findall(r'\[([^\]]+)\]', text)

    @classmethod
    def _citation_stats(cls, text: str) -> Dict[str, Any]:
        citations = cls._extract_citations(text)
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        with_cite = sum(1 for s in sentences if '[' in s and ']' in s)
        coverage = with_cite / len(sentences) if sentences else 0.0
        return {
            "total_citations": len(citations),
            "unique_citations": len(set(citations)),
            "citation_list": citations,
            "citation_coverage": round(coverage, 3),
        }

    @classmethod
    def process_mode_a(cls, text: str) -> Dict[str, Any]:
        """Process Mode A (Summarizer) — expects Markdown output."""
        stats = cls._citation_stats(text)
        return {
            "success": True,
            "raw_response": text,
            "citations": stats["citation_list"],
            "citation_coverage": stats["citation_coverage"],
        }

    @classmethod
    def process_mode_b(cls, text: str) -> Dict[str, Any]:
        """Process Mode B (Clause Classifier) — expects Markdown output."""
        stats = cls._citation_stats(text)
        # Extract clause types mentioned in the text
        clause_types = re.findall(r'\*\*Clause Type:\*\*\s*(.+)', text)
        citations = re.findall(r'\*\*Citation:\*\*\s*(.+)', text)
        return {
            "success": True,
            "raw_response": text,
            "clause_types_found": clause_types,
            "citations": citations or stats["citation_list"],
        }

    @classmethod
    def process_mode_c(cls, text: str) -> Dict[str, Any]:
        """Process Mode C (Case-Law IRAC) — expects IRAC Markdown."""
        sections: Dict[str, str] = {"issue": "", "rule": "", "application": "", "conclusion": ""}
        patterns = {
            "issue": r'\*\*Issue:\*\*\s*(.*?)(?=\*\*Rule:\*\*|$)',
            "rule": r'\*\*Rule:\*\*\s*(.*?)(?=\*\*Application:\*\*|$)',
            "application": r'\*\*Application:\*\*\s*(.*?)(?=\*\*Conclusion:\*\*|$)',
            "conclusion": r'\*\*Conclusion:\*\*\s*(.*?)$',
        }
        for key, pat in patterns.items():
            m = re.search(pat, text, re.DOTALL | re.IGNORECASE)
            if m:
                sections[key] = m.group(1).strip()

        stats = cls._citation_stats(text)
        insufficient = "insufficient basis" in text.lower()

        return {
            "success": not insufficient,
            "raw_response": text,
            "irac_structure": sections,
            "citations": stats["citation_list"],
            "citation_stats": stats,
            "error": "Insufficient basis from provided sources" if insufficient else None,
        }

    @classmethod
    def add_disclaimer(cls, text: str) -> str:
        return text + cls.LEGAL_DISCLAIMER
