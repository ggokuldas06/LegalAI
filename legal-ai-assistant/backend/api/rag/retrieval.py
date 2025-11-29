# api/rag/retrieval.py
from typing import List, Dict, Optional
import logging

from .embeddings import embedding_service
from .vector_store import get_vector_store

logger = logging.getLogger(__name__)


class RetrievalService:
    """Service for retrieving relevant document chunks"""
    
    def __init__(self):
        self.embedding_service = embedding_service
        self.vector_store = get_vector_store()
    
    def retrieve(
        self,
        query: str,
        k: int = 10,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Retrieve relevant chunks for a query
        
        Args:
            query: Search query
            k: Number of results
            filters: Optional filters (jurisdiction, year, keywords)
        
        Returns:
            List of relevant chunks with metadata and scores
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_service.encode_single(query)
            
            # Search vector store
            results = self.vector_store.search(
                query_embedding=query_embedding,
                k=k,
                filters=filters
            )
            
            logger.info(f"Retrieved {len(results)} chunks for query")
            
            # Format results for LLM context
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'chunk_id': result.get('chunk_id'),
                    'document_id': result.get('document_id'),
                    'title': result.get('title', 'Untitled'),
                    'case_name': result.get('title', 'Unknown'),  # For case law
                    'year': result.get('year', 'n.d.'),
                    'jurisdiction': result.get('jurisdiction', ''),
                    'text': result.get('text', ''),
                    'heading': result.get('heading', ''),
                    'score': result.get('score', 0.0),
                    'source': result.get('source', ''),
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Retrieval error: {e}", exc_info=True)
            return []
    
    def retrieve_for_mode_c(
        self,
        question: str,
        jurisdiction: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        keywords_include: Optional[List[str]] = None,
        keywords_exclude: Optional[List[str]] = None,
        k: int = 5
    ) -> List[Dict]:
        """
        Retrieve context passages for Mode C (Case-Law IRAC)
        
        Args:
            question: Legal question
            jurisdiction: Filter by jurisdiction
            year_from: Minimum year
            year_to: Maximum year
            keywords_include: Keywords that must be present
            keywords_exclude: Keywords that must not be present
            k: Number of results
        
        Returns:
            List of context passages formatted for Mode C prompts
        """
        filters = {}
        
        if jurisdiction:
            filters['jurisdiction'] = jurisdiction
        if year_from:
            filters['year_from'] = year_from
        if year_to:
            filters['year_to'] = year_to
        if keywords_include:
            filters['include'] = keywords_include
        if keywords_exclude:
            filters['exclude'] = keywords_exclude
        
        return self.retrieve(query=question, k=k, filters=filters)


# Global instance
retrieval_service = RetrievalService()