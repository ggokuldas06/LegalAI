# api/inference/prompts.py
from typing import Dict, List, Optional


# Ollama /api/chat uses a messages list — Gemma's template is handled by Ollama.
# Each message: {"role": "system"|"user"|"assistant", "content": "..."}


LEGAL_DISCLAIMER = (
    "\n\n---\n"
    "**DISCLAIMER:** This is informational analysis only and does not constitute "
    "legal advice. Consult a qualified attorney for legal guidance."
)


class SummarizerPrompt:
    """Mode A: Document summary in Markdown."""

    SYSTEM = (
        "You are a legal document summarizer. "
        "Produce a concise Markdown summary with these sections: "
        "## Executive Summary (2-3 bullets), "
        "## Key Points (4-6 bullets), "
        "## Risks (identified legal risks), "
        "## Obligations (key obligations and deadlines). "
        "Every bullet MUST include a citation: [Section X, paragraph Y]. "
        "Output raw Markdown only. Never fabricate information."
    )

    @classmethod
    def build_messages(cls, document_text: str, document_title: str) -> List[Dict]:
        user = (
            f"Analyze this legal document and provide a structured Markdown summary.\n\n"
            f"**Document:** {document_title}\n\n"
            f"**Text:**\n{document_text}\n\n"
            "Output structured Markdown with ## headings and bullet points. "
            "Cite every claim as [Section X, paragraph Y]. Never invent information."
        )
        return [
            {"role": "system", "content": cls.SYSTEM},
            {"role": "user", "content": user},
        ]


class ClauseClassifierPrompt:
    """Mode B: Clause detection and classification."""

    CLAUSE_TYPES = [
        "Termination", "Indemnity", "Confidentiality", "Intellectual Property",
        "Liability Caps", "Governing Law", "Payment Terms", "Warranties",
        "Force Majeure", "Assignment",
    ]

    SYSTEM = (
        "You are a contract clause classifier. "
        "For each clause found, output:\n"
        "**Clause Type:** <type>\n"
        "**Citation:** <nearest section header>\n"
        "**Confidence:** high | medium | low\n"
        "**Excerpt:** (verbatim text, preserve bullets and sub-points)\n"
        "---\n"
        "Rules: use the nearest section header as citation; never invent clause text; "
        "omit clause types not present; include full clause text without truncation. "
        "Output raw Markdown only."
    )

    @classmethod
    def build_messages(
        cls,
        document_text: str,
        document_title: str,
        clause_types: Optional[List[str]] = None,
    ) -> List[Dict]:
        types_str = ", ".join(clause_types or cls.CLAUSE_TYPES)
        user = (
            f"Extract the following clause types from this contract: {types_str}\n\n"
            f"**Document:** {document_title}\n\n"
            f"**Text:**\n{document_text}\n\n"
            "Follow the output format exactly. Only extract clauses that are clearly present."
        )
        return [
            {"role": "system", "content": cls.SYSTEM},
            {"role": "user", "content": user},
        ]


class CaseLawPrompt:
    """Mode C: Legal Q&A with adaptive format — IRAC for analysis, direct for lookups."""

    SYSTEM = (
        "You are a precise legal research assistant. "
        "Read the provided sources carefully and answer the question using the format that fits best:\n\n"
        "• **Factual lookup** (who, what, when, how much, which section): "
        "Answer directly in 1–3 sentences. Always cite the source inline as [Source N] or [Section X].\n\n"
        "• **Legal analysis** (whether X is permitted, what happens if Y, analyse/explain a clause, "
        "compare obligations, identify risks): "
        "Use IRAC structure:\n"
        "  **Issue:** State the legal question.\n"
        "  **Rule:** State the applicable clause or principle with citation.\n"
        "  **Application:** Apply the rule to the facts with citations.\n"
        "  **Conclusion:** Give a clear answer.\n\n"
        "RULES: Answer using ONLY the provided sources. "
        "Cite every factual claim as [Source N] or [Section X, Document Title]. "
        "If the sources do not contain the answer, say exactly: "
        "'The provided sources do not contain enough information to answer this question.' "
        "Never invent facts, names, numbers, or holdings."
    )

    @classmethod
    def build_messages(cls, question: str, context_passages: List[Dict]) -> List[Dict]:
        ctx = ""
        for i, p in enumerate(context_passages, 1):
            title = p.get("case_name") or p.get("title", "Unknown")
            year = p.get("year", "n.d.")
            heading = p.get("heading", "")
            section = p.get("section_path", "")
            text = p.get("text", "")
            loc = f" — {heading or section}" if (heading or section) else ""
            ctx += f"\n[Source {i}] {title} ({year}){loc}:\n{text}\n"

        user = (
            f"**Question:** {question}\n\n"
            f"**Relevant Sources:**\n{ctx}\n\n"
            "Choose the appropriate format (direct answer or IRAC) based on the question type, "
            "then answer using ONLY the sources above. Cite every claim."
        )
        return [
            {"role": "system", "content": cls.SYSTEM},
            {"role": "user", "content": user},
        ]


class PromptBuilder:
    """Factory: build Ollama chat messages for each mode."""

    @staticmethod
    def build_messages(mode: str, **kwargs) -> List[Dict]:
        if mode == "A":
            return SummarizerPrompt.build_messages(
                document_text=kwargs["document_text"],
                document_title=kwargs.get("document_title", "Untitled"),
            )
        elif mode == "B":
            return ClauseClassifierPrompt.build_messages(
                document_text=kwargs["document_text"],
                document_title=kwargs.get("document_title", "Untitled"),
                clause_types=kwargs.get("clause_types"),
            )
        elif mode == "C":
            return CaseLawPrompt.build_messages(
                question=kwargs["question"],
                context_passages=kwargs.get("context_passages", []),
            )
        else:
            raise ValueError(f"Unknown mode: {mode}")

    # Keep old name for backward compat
    @staticmethod
    def build_prompt(mode: str, **kwargs) -> List[Dict]:
        return PromptBuilder.build_messages(mode, **kwargs)
