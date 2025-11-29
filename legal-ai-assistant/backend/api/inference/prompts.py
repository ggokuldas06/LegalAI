# api/inference/prompts.py
from typing import Dict, List, Optional


class PromptTemplate:
    """Base class for prompt templates"""

    SYSTEM_INSTRUCTION = """You are a legal AI assistant. You provide informational analysis only, not legal advice. Always cite your sources and never fabricate information."""

    LEGAL_DISCLAIMER = """\n\n---\nDISCLAIMER: This is informational analysis only and does not constitute legal advice. Consult a qualified attorney for legal guidance."""

    @staticmethod
    def format_llama2_prompt(system: str, user_message: str) -> str:
        """Format prompt for LLaMA 2 Chat"""
        return f"""<s>[INST] <<SYS>>
{system}
<</SYS>>

{user_message} [/INST]"""


class SummarizerPrompt(PromptTemplate):
    """Mode A: Document Summarizer"""

    SYSTEM = """You are a legal document summarizer. Produce a clean, human-readable Markdown summary with these sections:

## Executive Summary
- 2–3 bullet points

## Key Points
- 4–6 important points

## Risks
- Identified legal risks

## Obligations
- Key obligations and deadlines

Every point MUST include a citation in the format: [Section X, paragraph Y].

IMPORTANT: Output **raw Markdown only**, and wrap the entire Markdown output inside a fenced code block annotated as `markdown`, for example:

```markdown
## Executive Summary
- ...
```

Do NOT output JSON, extraneous commentary, or any text outside the fenced code block. Never fabricate information."""

    @classmethod
    def build(cls, document_text: str, document_title: str) -> str:
        """Build summarizer prompt"""
        user_message = f"""Analyze this legal document and provide a Markdown summary.

Document: {document_title}

Text:
{document_text}

Return the summary in **raw Markdown syntax**, and wrap the entire Markdown output inside a fenced code block annotated as 'markdown'. Use this structure inside the code block:

```markdown
## Executive Summary
- point with [Section X, paragraph Y]

## Key Points
- point with [Section X, paragraph Y]

## Risks
- point with [Section X, paragraph Y]

## Obligations
- point with [Section X, paragraph Y]
```

Do not output anything outside the fenced code block, and do not output JSON. Never fabricate information."""

        return cls.format_llama2_prompt(cls.SYSTEM, user_message)


class ClauseClassifierPrompt(PromptTemplate):
    """Mode B: Clause Detection & Classification"""

    CLAUSE_TYPES = [
        'Termination',
        'Indemnity', 
        'Confidentiality',
        'Intellectual Property',
        'Liability Caps',
        'Governing Law',
        'Payment Terms',
        'Warranties',
        'Force Majeure',
        'Assignment',
    ]

    SYSTEM = SYSTEM = """You are a contract clause classifier. Detect and extract contract clauses and present them in a clear, human-readable format.
Task rules (CRITICAL):

For each clause you find, output the following fields in this exact order: Clause Type, Citation (nearest section header), Confidence (high/medium/low), Excerpt (verbatim, preserve original line breaks and bullets).

Use the nearest preceding section header (e.g., 'Section 3 — PAYMENT TERMS' or 'Section 4.2') to determine the citation. Do not guess a section number from nearby numbers in the text — use the actual header if present.

Include full clause text (do not truncate). If the clause contains sub-points or bullets, include them all verbatim.

If a clause spans multiple sections, indicate the range (e.g., 'Section 6.1–6.3').

If a clause is present but unclear, mark confidence 'medium' and explain in one short parenthetical note why.

If a clause type is not present, do NOT fabricate — simply omit it.

Do NOT output JSON. Provide a human-readable Markdown list of clauses, wrapped in a fenced code block annotated as text (or markdown), so the output is preserved exactly.

Preferred output layout inside fenced block (literal example — follow this structure exactly):

text
Copy code
Clause Type: Confidentiality
Citation: Section 4 — CONFIDENTIALITY
Confidence: high
Excerpt:
Both Parties must maintain strict confidentiality over Confidential Information.
Confidentiality obligations survive for 5 years following termination.
Forbidden Activities:
  (a) disclose scientific research data to third parties;
  (b) decompile or reverse engineer proprietary tools;
  (c) store Client data in non-approved cloud environments.

----
Clause Type: Payment Terms
Citation: Section 3 — PAYMENT TERMS
Confidence: high
Excerpt:
3.1 Fees. Client shall compensate Service Provider at $250/hour for engineering work and $300/hour for compliance-oriented consulting.
3.2 Monthly Invoicing. Invoices must include itemized time logs.
3.3 Late Payments. Any invoice not paid within 30 days accrues 1.25% monthly interest.

----
[and so on...]
Only output clauses found in the document. Never invent clause text or citations. Keep the output inside the single fenced code block and do not add extra commentary outside the block."""

    @classmethod
    def build(cls, document_text: str, document_title: str, 
              clause_types: Optional[List[str]] = None) -> str:
        """Build clause classifier prompt"""
        types = clause_types or cls.CLAUSE_TYPES
        types_str = ", ".join(types)

        user_message = f"""Analyze this contract and extract the following clause types: {types_str}

Document: {document_title}

Text:
{document_text}

Follow the output format and rules specified in the system instructions exactly.

Only extract clauses that are clearly present. Do not fabricate."""

        return cls.format_llama2_prompt(cls.SYSTEM, user_message)


class CaseLawPrompt(PromptTemplate):
    """Mode C: Case-Law IRAC Q&A"""

    SYSTEM = """You are a legal research assistant specializing in case law analysis. Answer questions using IRAC structure:

I - Issue: What is the legal question?
R - Rule: What legal principles apply? (with case citations)
A - Application: How do cases apply to this situation? (with citations)
C - Conclusion: What is the answer? (with citations)

CRITICAL RULES:
1. EVERY factual claim must have a citation in format: [Case Name, Year]
2. If you don't have sufficient information, say "Insufficient basis from provided sources"
3. Never invent case names or holdings
4. Be precise and cautious"""

    @classmethod
    def build(cls, question: str, context_passages: List[Dict[str, str]]) -> str:
        """Build case law Q&A prompt with retrieved context"""

        # Format context passages
        context_str = ""
        for i, passage in enumerate(context_passages, 1):
            case_name = passage.get('case_name', 'Unknown')
            year = passage.get('year', 'n.d.')
            text = passage.get('text', '')

            context_str += f"\n[{i}] {case_name} ({year}):\n{text}\n"

        user_message = f"""Question: {question}

Relevant Case Law:
{context_str}

Provide an IRAC-structured answer using ONLY the provided sources. Cite every claim.

Format:
**Issue:**
[State the legal question]

**Rule:**
[Legal principles with citations]

**Application:**
[How cases apply with citations]

**Conclusion:**
[Answer with supporting citations]"""

        return cls.format_llama2_prompt(cls.SYSTEM, user_message)


class PromptBuilder:
    """Factory for building prompts"""

    @staticmethod
    def build_prompt(mode: str, **kwargs) -> str:
        """
        Build prompt for specified mode

        Args:
            mode: 'A', 'B', or 'C'
            **kwargs: Mode-specific parameters

        Returns:
            Formatted prompt string
        """
        if mode == 'A':
            return SummarizerPrompt.build(
                document_text=kwargs['document_text'],
                document_title=kwargs.get('document_title', 'Untitled')
            )

        elif mode == 'B':
            return ClauseClassifierPrompt.build(
                document_text=kwargs['document_text'],
                document_title=kwargs.get('document_title', 'Untitled'),
                clause_types=kwargs.get('clause_types')
            )

        elif mode == 'C':
            return CaseLawPrompt.build(
                question=kwargs['question'],
                context_passages=kwargs.get('context_passages', [])
            )

        else:
            raise ValueError(f"Unknown mode: {mode}")
