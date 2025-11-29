from __future__ import annotations
from typing import Optional, Dict, Any, List
# api/inference/post_processor.py
import json
import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ResponseProcessor:
    """Post-process LLM responses"""
    
    LEGAL_DISCLAIMER = "\n\n---\n**DISCLAIMER:** This is informational analysis only and does not constitute legal advice. Consult a qualified attorney for legal guidance."
    
    @staticmethod
    def extract_json(text: str) -> Optional[Dict]:
        """Extract JSON from text that might contain other content"""
        try:
            # Try direct parse first
            return json.loads(text.strip())
        except json.JSONDecodeError:
            # Try to find JSON in the text
            json_match = re.search(r'\{.*\}|\[.*\]', text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass
        
        logger.warning("Could not extract valid JSON from response")
        return None
    
    @staticmethod
    def validate_citations(text: str) -> Dict[str, Any]:
        """Check citation coverage in response"""
        # Find all citations like [Source, Year] or [Section X]
        citations = re.findall(r'\[([^\]]+)\]', text)
        
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        sentences_with_citations = 0
        for sentence in sentences:
            if '[' in sentence and ']' in sentence:
                sentences_with_citations += 1
        
        citation_coverage = 0
        if sentences:
            citation_coverage = sentences_with_citations / len(sentences)
        
        return {
            'total_citations': len(citations),
            'unique_citations': len(set(citations)),
            'citation_list': citations,
            'sentence_count': len(sentences),
            'sentences_with_citations': sentences_with_citations,
            'citation_coverage': citation_coverage,
        }
    
    @classmethod
    def process_mode_a(cls, response_text: str) -> Dict[str, Any]:
        """Process Mode A (Summarizer) response"""
        result = {
            'raw_response': response_text,
            'success': False,
            'error': None,
            'summary': None,
            'citations': [],
        }
        
        # Extract JSON
        summary_json = cls.extract_json(response_text)
        
        if summary_json:
            result['success'] = True
            result['summary'] = summary_json
            
            # Extract citations from all fields
            all_text = json.dumps(summary_json)
            citation_info = cls.validate_citations(all_text)
            result['citations'] = citation_info['citation_list']
            result['citation_coverage'] = citation_info['citation_coverage']
        else:
            result['error'] = "Invalid JSON format in response"
        
        return result
    
    @classmethod
    def process_mode_b(cls, response_text: str) -> Dict[str, Any]:
        """Process Mode B (Clause Classifier) response"""
        result = {
            'raw_response': response_text,
            'success': False,
            'error': None,
            'clauses': [],
            'citations': [],
        }
        
        # Extract JSON array
        clauses_json = cls.extract_json(response_text)
        
        if clauses_json and isinstance(clauses_json, list):
            result['success'] = True
            result['clauses'] = clauses_json
            
            # Extract citations
            citations = []
            for clause in clauses_json:
                if 'citation' in clause:
                    citations.append(clause['citation'])
            
            result['citations'] = citations
        else:
            result['error'] = "Invalid JSON array format in response"
        
        return result
    
    @classmethod
    def process_mode_c(cls, response_text: str) -> Dict[str, Any]:
        """Process Mode C (Case-Law IRAC) response"""
        result = {
            'raw_response': response_text,
            'success': True,
            'irac_structure': {},
            'citations': [],
            'citation_stats': {},
        }
        
        # Parse IRAC sections
        sections = {
            'issue': '',
            'rule': '',
            'application': '',
            'conclusion': '',
        }
        
        # Extract sections using regex
        patterns = {
            'issue': r'\*\*Issue:\*\*\s*(.*?)(?=\*\*Rule:\*\*|$)',
            'rule': r'\*\*Rule:\*\*\s*(.*?)(?=\*\*Application:\*\*|$)',
            'application': r'\*\*Application:\*\*\s*(.*?)(?=\*\*Conclusion:\*\*|$)',
            'conclusion': r'\*\*Conclusion:\*\*\s*(.*?)$',
        }
        
        for section, pattern in patterns.items():
            match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
            if match:
                sections[section] = match.group(1).strip()
        
        result['irac_structure'] = sections
        
        # Validate citations
        citation_info = cls.validate_citations(response_text)
        result['citations'] = citation_info['citation_list']
        result['citation_stats'] = citation_info
        
        # Check if response indicates insufficient information
        if 'insufficient basis' in response_text.lower():
            result['success'] = False
            result['error'] = "Insufficient information in provided sources"
        
        return result
    
    @classmethod
    def add_disclaimer(cls, response_text: str) -> str:
        """Add legal disclaimer to response"""
        return response_text + cls.LEGAL_DISCLAIMER