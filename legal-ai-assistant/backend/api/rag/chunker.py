# api/rag/chunker.py
import re
import nltk
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class DocumentChunker:
    """Chunk documents into semantically meaningful segments"""
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        min_chunk_size: int = 50
    ):
        """
        Args:
            chunk_size: Target size for chunks (in characters)
            chunk_overlap: Overlap between consecutive chunks
            min_chunk_size: Minimum chunk size to keep
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def chunk_text(
        self,
        text: str,
        document_title: str = "",
        metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Chunk text into overlapping segments
        
        Args:
            text: Text to chunk
            document_title: Document title for context
            metadata: Additional metadata to include
        
        Returns:
            List of chunk dictionaries with text and metadata
        """
        # Clean text
        text = self._clean_text(text)
        
        # Try to split by sections first
        sections = self._split_by_sections(text)
        
        chunks = []
        char_position = 0
        
        for section_idx, section in enumerate(sections):
            section_heading = section.get('heading', '')
            section_text = section.get('text', '')
            
            # If section is small enough, keep as single chunk
            if len(section_text) <= self.chunk_size:
                chunks.append({
                    'ord': len(chunks),
                    'text': section_text,
                    'heading': section_heading,
                    'char_start': char_position,
                    'char_end': char_position + len(section_text),
                    'metadata': metadata or {}
                })
                char_position += len(section_text)
            else:
                # Split large sections into smaller chunks
                sub_chunks = self._split_text(
                    section_text,
                    char_position,
                    section_heading
                )
                for chunk in sub_chunks:
                    chunk['ord'] = len(chunks)
                    chunk['metadata'] = metadata or {}
                    chunks.append(chunk)
                    char_position = chunk['char_end']
        
        logger.info(f"Created {len(chunks)} chunks from document")
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove page numbers and common artifacts
        text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
        return text.strip()
    
    def _split_by_sections(self, text: str) -> List[Dict]:
        """
        Split text by sections (using headers)
        """
        # Common section patterns in legal documents
        section_patterns = [
            r'\n\s*(?:SECTION|Section|Article|ARTICLE)\s+[IVX\d]+[.:\s]',
            r'\n\s*[IVX\d]+\.\s+[A-Z][A-Z\s]{3,}',
            r'\n\s*\d+\.\s+[A-Z][A-Z\s]{3,}',
        ]
        
        sections = []
        current_heading = ""
        current_text = ""
        
        lines = text.split('\n')
        
        for line in lines:
            # Check if line is a section header
            is_header = False
            for pattern in section_patterns:
                if re.match(pattern, '\n' + line):
                    # Save previous section
                    if current_text.strip():
                        sections.append({
                            'heading': current_heading.strip(),
                            'text': current_text.strip()
                        })
                    
                    current_heading = line.strip()
                    current_text = ""
                    is_header = True
                    break
            
            if not is_header:
                current_text += line + "\n"
        
        # Add final section
        if current_text.strip():
            sections.append({
                'heading': current_heading.strip(),
                'text': current_text.strip()
            })
        
        # If no sections found, return entire text
        if not sections:
            sections = [{'heading': '', 'text': text}]
        
        return sections
    
    def _split_text(
        self,
        text: str,
        start_position: int,
        heading: str = ""
    ) -> List[Dict]:
        """
        Split text into chunks with overlap
        """
        chunks = []
        
        # Split by sentences
        sentences = nltk.sent_tokenize(text)
        
        current_chunk = ""
        chunk_start = start_position
        
        for sentence in sentences:
            # Check if adding sentence exceeds chunk size
            if len(current_chunk) + len(sentence) > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append({
                    'text': current_chunk.strip(),
                    'heading': heading,
                    'char_start': chunk_start,
                    'char_end': chunk_start + len(current_chunk)
                })
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap(current_chunk)
                current_chunk = overlap_text + " " + sentence
                chunk_start = chunk_start + len(current_chunk) - len(overlap_text)
            else:
                current_chunk += " " + sentence if current_chunk else sentence
        
        # Add final chunk
        if current_chunk.strip() and len(current_chunk.strip()) >= self.min_chunk_size:
            chunks.append({
                'text': current_chunk.strip(),
                'heading': heading,
                'char_start': chunk_start,
                'char_end': chunk_start + len(current_chunk)
            })
        
        return chunks
    
    def _get_overlap(self, text: str) -> str:
        """Get overlap text from end of chunk"""
        if len(text) <= self.chunk_overlap:
            return text
        
        # Try to get overlap at sentence boundary
        sentences = nltk.sent_tokenize(text)
        overlap = ""
        
        for sentence in reversed(sentences):
            if len(overlap) + len(sentence) <= self.chunk_overlap:
                overlap = sentence + " " + overlap
            else:
                break
        
        # Fallback to character-based overlap
        if not overlap:
            overlap = text[-self.chunk_overlap:]
        
        return overlap.strip()


# Factory function
def create_chunker(chunk_size: int = 500, chunk_overlap: int = 100) -> DocumentChunker:
    """Create a document chunker with specified parameters"""
    return DocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)