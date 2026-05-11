# api/rag/chunker.py
import re
import nltk
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Heading level constants
H1, H2, H3 = 1, 2, 3
TABLE = "table"
TEXT = "text"


class StructureNode:
    """Represents a structural unit in a document"""
    def __init__(self, level, heading: str, text: str, node_type=TEXT):
        self.level = level        # H1, H2, H3, or None for text/table
        self.heading = heading
        self.text = text          # Raw text content (not including sub-nodes)
        self.node_type = node_type  # TEXT or TABLE
        self.children: List["StructureNode"] = []

    def full_text(self) -> str:
        """Full text including all children"""
        parts = []
        if self.heading:
            parts.append(self.heading)
        if self.text:
            parts.append(self.text)
        for child in self.children:
            parts.append(child.full_text())
        return "\n\n".join(p for p in parts if p.strip())

    def full_length(self) -> int:
        return len(self.full_text())


class HierarchicalChunker:
    """
    Structure-aware hierarchical recursive chunker.

    Parsing order: H2 sections → if too large, split by H3 → if still too large, split by paragraphs/sentences.
    Tables are always kept as atomic chunks.
    """

    # Markdown headings
    _MD_H1 = re.compile(r'^# (.+)$', re.MULTILINE)
    _MD_H2 = re.compile(r'^## (.+)$', re.MULTILINE)
    _MD_H3 = re.compile(r'^### (.+)$', re.MULTILINE)

    # Legal document section patterns (legal docs often use ALL CAPS or numbered headings)
    _LEGAL_H1 = re.compile(
        r'^(CHAPTER|PART|TITLE)\s+[IVXLCDM\d]+[.:]?\s*.+$', re.MULTILINE | re.IGNORECASE
    )
    _LEGAL_H2 = re.compile(
        r'^(SECTION|ARTICLE|§)\s+[IVXLCDM\d]+[.:]?\s*.+$|'
        r'^\d+\.\s{1,4}[A-Z][A-Z\s]{3,}$',
        re.MULTILINE
    )
    _LEGAL_H3 = re.compile(
        r'^\d+\.\d+\.?\s+.+$|'        # 1.1 or 1.1. heading
        r'^[a-z]\)\s+[A-Z].+$|'       # a) Heading
        r'^\([ivxlcdm]+\)\s+[A-Z].+$',  # (i) Heading
        re.MULTILINE
    )

    # Table detection: lines of pipe-separated cells or dashed borders
    _TABLE_ROW = re.compile(r'^\|.+\|$', re.MULTILINE)
    _TABLE_BORDER = re.compile(r'^[-|+]{3,}$', re.MULTILINE)

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
        min_chunk_size: int = 80,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chunk_text(
        self,
        text: str,
        document_title: str = "",
        metadata: Optional[Dict] = None,
    ) -> List[Dict]:
        """
        Chunk text using structure-aware hierarchical splitting.
        Returns list of chunk dicts with text, heading, section_path, metadata.
        """
        metadata = metadata or {}
        text = self._normalize(text)

        # Extract tables before structural parsing (they're atomic)
        text, tables = self._extract_tables(text)

        # Parse into structural tree
        nodes = self._parse_structure(text)

        # Flatten nodes into chunks recursively
        raw_chunks: List[Dict] = []
        for node in nodes:
            self._flatten_node(node, raw_chunks, parent_path=[])

        # Re-inject table chunks at their approximate positions
        for tbl in tables:
            raw_chunks.append({
                "text": tbl,
                "heading": "[Table]",
                "section_path": [],
                "node_type": TABLE,
            })

        # Assign sequential ids and merge metadata
        chunks = []
        for i, chunk in enumerate(raw_chunks):
            if len(chunk["text"].strip()) < self.min_chunk_size:
                continue
            chunks.append({
                "ord": len(chunks),
                "text": chunk["text"].strip(),
                "heading": chunk.get("heading", ""),
                "section_path": " > ".join(chunk.get("section_path", [])),
                "node_type": chunk.get("node_type", TEXT),
                "metadata": metadata,
            })

        logger.info(f"Created {len(chunks)} chunks (incl. {len(tables)} tables)")
        return chunks

    # ------------------------------------------------------------------
    # Structure parsing
    # ------------------------------------------------------------------

    def _parse_structure(self, text: str) -> List[StructureNode]:
        """Parse text into structural nodes at H1/H2/H3 levels."""
        lines = text.split("\n")
        nodes: List[StructureNode] = []
        current_h1 = StructureNode(H1, "", "")
        current_h2: Optional[StructureNode] = None
        current_h3: Optional[StructureNode] = None
        buffer: List[str] = []

        def flush_buffer(target_node: Optional[StructureNode]):
            if buffer and target_node is not None:
                target_node.text += "\n".join(buffer) + "\n"
            buffer.clear()

        for line in lines:
            level, heading = self._detect_heading(line)

            if level == H1:
                flush_buffer(current_h3 or current_h2 or current_h1)
                if current_h1.heading or current_h1.text or current_h1.children:
                    nodes.append(current_h1)
                current_h1 = StructureNode(H1, heading, "")
                current_h2 = None
                current_h3 = None

            elif level == H2:
                flush_buffer(current_h3 or current_h2 or current_h1)
                current_h2 = StructureNode(H2, heading, "")
                current_h3 = None
                current_h1.children.append(current_h2)

            elif level == H3:
                flush_buffer(current_h3 or current_h2 or current_h1)
                current_h3 = StructureNode(H3, heading, "")
                if current_h2:
                    current_h2.children.append(current_h3)
                else:
                    current_h1.children.append(current_h3)

            else:
                buffer.append(line)

        flush_buffer(current_h3 or current_h2 or current_h1)
        nodes.append(current_h1)

        # If we only got a single unnamed root with no children, treat as flat
        if len(nodes) == 1 and not nodes[0].heading and not nodes[0].children:
            return [nodes[0]]

        return [n for n in nodes if n.heading or n.text.strip() or n.children]

    def _detect_heading(self, line: str) -> Tuple[Optional[int], str]:
        """Return (level, heading_text) for a line, or (None, '') if not a heading."""
        stripped = line.strip()
        if not stripped:
            return None, ""

        # Markdown headings take priority
        if stripped.startswith("### "):
            return H3, stripped[4:].strip()
        if stripped.startswith("## "):
            return H2, stripped[3:].strip()
        if stripped.startswith("# ") and not stripped.startswith("##"):
            return H1, stripped[2:].strip()

        # Legal H1 patterns
        if self._LEGAL_H1.match(stripped):
            return H1, stripped

        # Legal H2 patterns
        if self._LEGAL_H2.match(stripped):
            return H2, stripped

        # Legal H3 patterns
        if self._LEGAL_H3.match(stripped):
            return H3, stripped

        return None, ""

    # ------------------------------------------------------------------
    # Flattening / recursive splitting
    # ------------------------------------------------------------------

    def _flatten_node(
        self,
        node: StructureNode,
        out: List[Dict],
        parent_path: List[str],
    ):
        """Recursively flatten a node tree into chunks."""
        path = parent_path + ([node.heading] if node.heading else [])

        if node.node_type == TABLE:
            out.append({"text": node.text, "heading": node.heading,
                        "section_path": path, "node_type": TABLE})
            return

        if not node.children:
            # Leaf node — split by size
            self._emit_leaf(node.text, node.heading, path, out)
            return

        # Node has children: emit own text as a preamble chunk if non-trivial
        if len(node.text.strip()) >= self.min_chunk_size:
            self._emit_leaf(node.text, node.heading, path, out)

        for child in node.children:
            self._flatten_node(child, out, path)

    def _emit_leaf(self, text: str, heading: str, path: List[str], out: List[Dict]):
        """Emit one or more chunks from leaf text."""
        text = text.strip()
        if not text:
            return

        if len(text) <= self.chunk_size:
            out.append({"text": text, "heading": heading, "section_path": path})
            return

        # Text is too big — split into overlapping sentence-based chunks
        sub_chunks = self._sentence_split(text, heading)
        for sc in sub_chunks:
            out.append({"text": sc, "heading": heading, "section_path": path})

    def _sentence_split(self, text: str, heading: str) -> List[str]:
        """Split oversized text into overlapping sentence-based chunks."""
        try:
            sentences = nltk.sent_tokenize(text)
        except Exception:
            # Fallback: split by double newline, then by chunk_size
            sentences = [p for p in text.split("\n\n") if p.strip()]

        chunks = []
        current = ""
        overlap_buffer = ""

        for sent in sentences:
            if len(current) + len(sent) > self.chunk_size and current:
                if len(current.strip()) >= self.min_chunk_size:
                    chunks.append(current.strip())
                # Overlap: take last N chars at sentence boundary
                overlap_buffer = self._get_overlap(current)
                current = overlap_buffer + " " + sent
            else:
                current = (current + " " + sent).strip() if current else sent

        if current.strip() and len(current.strip()) >= self.min_chunk_size:
            chunks.append(current.strip())

        return chunks if chunks else [text[: self.chunk_size]]

    def _get_overlap(self, text: str) -> str:
        """Extract overlap text (last ~chunk_overlap chars at sentence boundary)."""
        if len(text) <= self.chunk_overlap:
            return text
        try:
            sentences = nltk.sent_tokenize(text)
        except Exception:
            return text[-self.chunk_overlap:]

        overlap = ""
        for sent in reversed(sentences):
            if len(overlap) + len(sent) <= self.chunk_overlap:
                overlap = sent + " " + overlap
            else:
                break
        return overlap.strip() or text[-self.chunk_overlap:]

    # ------------------------------------------------------------------
    # Table extraction
    # ------------------------------------------------------------------

    def _extract_tables(self, text: str) -> Tuple[str, List[str]]:
        """
        Extract Markdown-style tables from text, replace with placeholders.
        Returns (cleaned_text, list_of_table_strings).
        """
        tables: List[str] = []
        lines = text.split("\n")
        result_lines: List[str] = []
        in_table = False
        table_lines: List[str] = []

        for line in lines:
            is_table_line = bool(self._TABLE_ROW.match(line.strip())) or \
                            bool(self._TABLE_BORDER.match(line.strip()))

            if is_table_line:
                in_table = True
                table_lines.append(line)
            else:
                if in_table:
                    tables.append("\n".join(table_lines))
                    result_lines.append(f"[TABLE_{len(tables) - 1}]")
                    table_lines = []
                    in_table = False
                result_lines.append(line)

        if table_lines:
            tables.append("\n".join(table_lines))
            result_lines.append(f"[TABLE_{len(tables) - 1}]")

        return "\n".join(result_lines), tables

    # ------------------------------------------------------------------
    # Text normalization
    # ------------------------------------------------------------------

    def _normalize(self, text: str) -> str:
        """Normalize whitespace without destroying structure."""
        # Collapse runs of 3+ blank lines to 2
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Strip trailing whitespace per line
        text = "\n".join(line.rstrip() for line in text.split("\n"))
        return text.strip()


def create_chunker(chunk_size: int = 800, chunk_overlap: int = 150) -> HierarchicalChunker:
    return HierarchicalChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
