"""Query Decomposer - Extract scheme names and entities from queries

This module provides intelligent query understanding to extract:
- Scheme names (PMEGP, MUDRA, Stand-Up India, etc.)
- Query type classification
- Entity normalization and fuzzy matching

Used for metadata-aware retrieval to guarantee scheme-specific accuracy.
"""
import re
from typing import List, Dict, Optional, Tuple
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from src.logger import setup_logger
import config

logger = setup_logger(__name__)


class QueryDecomposer:
    """Extract scheme names and entities from user queries"""
    
    # Common Indian government scheme acronyms and full names
    KNOWN_SCHEMES = {
        # MSME & Entrepreneurship
        'PMEGP': ['PMEGP', 'Prime Minister Employment Generation Programme', 'PM Employment Generation'],
        'MUDRA': ['MUDRA', 'Micro Units Development Refinance Agency', 'MUDRA Loan', 'Pradhan Mantri MUDRA Yojana'],
        'CGTMSE': ['CGTMSE', 'Credit Guarantee Fund Trust for Micro and Small Enterprises'],
        'STAND UP INDIA': ['Stand Up India', 'Stand-Up India', 'Standup India'],
        'STARTUP INDIA': ['Startup India', 'Start-up India', 'Start Up India'],
        
        # Rural & Agriculture
        'PMKSY': ['PMKSY', 'Pradhan Mantri Krishi Sinchayee Yojana', 'PM Krishi Sinchayee'],
        'PM-KISAN': ['PM-KISAN', 'PM KISAN', 'Pradhan Mantri Kisan Samman Nidhi'],
        'PMFBY': ['PMFBY', 'Pradhan Mantri Fasal Bima Yojana', 'PM Fasal Bima'],
        
        # Housing & Urban
        'PMAY': ['PMAY', 'Pradhan Mantri Awas Yojana', 'PM Awas Yojana'],
        'AMRUT': ['AMRUT', 'Atal Mission for Rejuvenation and Urban Transformation'],
        
        # Education & Skill
        'PMKVY': ['PMKVY', 'Pradhan Mantri Kaushal Vikas Yojana', 'PM Kaushal Vikas'],
        'NSP': ['NSP', 'National Scholarship Portal'],
        
        # Healthcare
        'PMJAY': ['PMJAY', 'Pradhan Mantri Jan Arogya Yojana', 'Ayushman Bharat'],
        
        # Financial Inclusion
        'PMJDY': ['PMJDY', 'Pradhan Mantri Jan Dhan Yojana', 'PM Jan Dhan'],
        'APY': ['APY', 'Atal Pension Yojana'],
        
        # Energy
        'PMUY': ['PMUY', 'Pradhan Mantri Ujjwala Yojana', 'PM Ujjwala'],
        
        # Infrastructure
        'PMGSY': ['PMGSY', 'Pradhan Mantri Gram Sadak Yojana', 'PM Gram Sadak']
    }
    
    def __init__(self):
        """Initialize query decomposer with Ollama LLM"""
        self.llm = ChatOllama(
            model=config.OLLAMA_MODEL,
            temperature=0.1,  # Low temperature for precise extraction
            base_url=config.OLLAMA_BASE_URL
        )
        
        # Build reverse lookup map for fast matching
        self._build_scheme_lookup()
        
        logger.info(f"QueryDecomposer initialized with {len(self.KNOWN_SCHEMES)} known schemes")
    
    def _build_scheme_lookup(self):
        """Build reverse lookup map: variant -> canonical name"""
        self.scheme_lookup = {}
        for canonical, variants in self.KNOWN_SCHEMES.items():
            for variant in variants:
                # Store lowercase for case-insensitive matching
                self.scheme_lookup[variant.lower()] = canonical
        
        logger.debug(f"Built scheme lookup with {len(self.scheme_lookup)} variants")
    
    def _extract_with_regex(self, query: str) -> List[str]:
        """Fast regex-based extraction for known scheme patterns"""
        found_schemes = set()
        query_lower = query.lower()
        
        # Direct substring matching
        for variant, canonical in self.scheme_lookup.items():
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(variant) + r'\b'
            if re.search(pattern, query_lower, re.IGNORECASE):
                found_schemes.add(canonical)
                logger.debug(f"Regex match: '{variant}' -> {canonical}")
        
        return list(found_schemes)
    
    def _extract_with_llm(self, query: str) -> List[str]:
        """LLM-based extraction for complex/ambiguous queries"""
        prompt = PromptTemplate(
            template="""Extract government scheme names from the query.

Query: {query}

Known schemes include: PMEGP, MUDRA, CGTMSE, Stand Up India, Startup India, PMKSY, PM-KISAN, PMAY, PMKVY, PMJAY, PMJDY, and others.

Instructions:
1. Identify any government scheme names mentioned
2. Return ONLY the scheme names, separated by commas
3. Use standard acronyms (e.g., PMEGP not "Prime Minister Employment Generation Programme")
4. If no schemes found, return "NONE"

Scheme names:""",
            input_variables=["query"]
        )
        
        try:
            chain = prompt | self.llm
            response = chain.invoke({"query": query})
            
            # Parse response
            result = response.content.strip().upper()
            
            if result == "NONE" or not result:
                return []
            
            # Split by comma and clean
            extracted = [s.strip() for s in result.split(',')]
            
            # Normalize to canonical names
            normalized = []
            for scheme in extracted:
                # Try to find in lookup
                canonical = self.scheme_lookup.get(scheme.lower())
                if canonical:
                    normalized.append(canonical)
                    logger.debug(f"LLM extraction: '{scheme}' -> {canonical}")
                elif scheme in self.KNOWN_SCHEMES:
                    normalized.append(scheme)
                    logger.debug(f"LLM extraction: '{scheme}' (already canonical)")
            
            return normalized
            
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}. Falling back to regex.")
            return []
    
    def extract_scheme_names(self, query: str) -> List[str]:
        """Extract scheme names using hybrid approach (regex + LLM)
        
        Args:
            query: User query
            
        Returns:
            List of canonical scheme names found in query
        """
        logger.info(f"Extracting scheme names from: '{query[:80]}...'")
        
        # First try fast regex extraction
        regex_schemes = self._extract_with_regex(query)
        
        if regex_schemes:
            logger.info(f"Regex extraction found: {regex_schemes}")
            return regex_schemes
        
        # Fallback to LLM for complex queries
        logger.debug("No regex matches, trying LLM extraction...")
        llm_schemes = self._extract_with_llm(query)
        
        if llm_schemes:
            logger.info(f"LLM extraction found: {llm_schemes}")
            return llm_schemes
        
        logger.info("No scheme names detected in query")
        return []
    
    def classify_query_type(self, query: str, detected_schemes: List[str]) -> Dict[str, any]:
        """Classify query type for routing decision
        
        Returns:
            {
                'has_scheme': bool,
                'schemes': List[str],
                'retrieval_mode': 'filtered' | 'hybrid',
                'confidence': float
            }
        """
        has_scheme = len(detected_schemes) > 0
        
        classification = {
            'has_scheme': has_scheme,
            'schemes': detected_schemes,
            'retrieval_mode': 'filtered' if has_scheme else 'hybrid',
            'confidence': 1.0 if detected_schemes else 0.8  # High confidence with schemes
        }
        
        logger.info(
            f"Query classification: mode={classification['retrieval_mode']}, "
            f"schemes={detected_schemes}, confidence={classification['confidence']}"
        )
        
        return classification
    
    def decompose(self, query: str) -> Dict[str, any]:
        """Complete query decomposition pipeline
        
        Args:
            query: User query
            
        Returns:
            {
                'original_query': str,
                'detected_schemes': List[str],
                'retrieval_mode': 'filtered' | 'hybrid',
                'filter_params': Dict (Qdrant filter params if filtered mode)
            }
        """
        # Extract scheme names
        detected_schemes = self.extract_scheme_names(query)
        
        # Classify query
        classification = self.classify_query_type(query, detected_schemes)
        
        # Build result
        result = {
            'original_query': query,
            'detected_schemes': detected_schemes,
            'retrieval_mode': classification['retrieval_mode'],
            'confidence': classification['confidence']
        }
        
        # Add filter params if using filtered mode
        if classification['retrieval_mode'] == 'filtered':
            result['filter_params'] = self._build_filter_params(detected_schemes)
        
        return result
    
    def _build_filter_params(self, scheme_names: List[str]) -> Dict:
        """Build Qdrant filter parameters for scheme names
        
        Args:
            scheme_names: List of canonical scheme names
            
        Returns:
            Qdrant filter dict compatible with qdrant_client.models.Filter
        """
        if len(scheme_names) == 1:
            # Single scheme - simple match
            return {
                'must': [
                    {
                        'key': 'scheme_name',
                        'match': {'value': scheme_names[0]}
                    }
                ]
            }
        else:
            # Multiple schemes - match any
            return {
                'must': [
                    {
                        'key': 'scheme_name',
                        'match': {'any': scheme_names}
                    }
                ]
            }


# Global instance for reuse
_query_decomposer = None

def get_query_decomposer() -> QueryDecomposer:
    """Get or create global query decomposer instance"""
    global _query_decomposer
    if _query_decomposer is None:
        _query_decomposer = QueryDecomposer()
    return _query_decomposer


if __name__ == "__main__":
    # Test the query decomposer
    decomposer = QueryDecomposer()
    
    test_queries = [
        "Can women entrepreneurs apply for PMEGP?",
        "What is the subsidy amount in MUDRA scheme?",
        "Compare PMEGP and Stand Up India schemes",
        "What are the manufacturing subsidy schemes?",  # No specific scheme
        "How to apply for Pradhan Mantri MUDRA Yojana?",
        "CGTMSE loan guarantee eligibility criteria"
    ]
    
    print("\n" + "="*80)
    print("QUERY DECOMPOSER TEST")
    print("="*80 + "\n")
    
    for query in test_queries:
        print(f"Query: {query}")
        result = decomposer.decompose(query)
        print(f"  Detected: {result['detected_schemes']}")
        print(f"  Mode: {result['retrieval_mode']}")
        if result.get('filter_params'):
            print(f"  Filter: {result['filter_params']}")
        print()
