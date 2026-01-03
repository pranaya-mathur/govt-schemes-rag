"""Query Decomposer - Extract scheme names and entities from queries

Dynamically loads ALL scheme names from Qdrant and uses fuzzy matching
to handle variations, typos, and acronyms.

No hardcoded schemes - adapts automatically to database content.
"""
import re
from typing import List, Dict, Optional, Set
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from src.logger import setup_logger
import config

try:
    from rapidfuzz import fuzz, process
    FUZZY_MATCHING_AVAILABLE = True
except ImportError:
    FUZZY_MATCHING_AVAILABLE = False
    logger = setup_logger(__name__)
    logger.warning("rapidfuzz not installed. Fuzzy matching disabled. Install: pip install rapidfuzz")

logger = setup_logger(__name__)


class QueryDecomposer:
    """Extract scheme names from queries using dynamic loading + fuzzy matching"""
    
    def __init__(self, qdrant_client=None, collection_name: str = None):
        """Initialize query decomposer with dynamic scheme loading
        
        Args:
            qdrant_client: Optional Qdrant client for loading schemes
            collection_name: Optional collection name
        """
        self.llm = ChatOllama(
            model=config.OLLAMA_MODEL,
            temperature=0.1,  # Low temperature for precise extraction
            base_url=config.OLLAMA_BASE_URL
        )
        
        self.qdrant_client = qdrant_client
        self.collection_name = collection_name or config.COLLECTION_NAME
        
        # Dynamic scheme list (loaded from Qdrant)
        self.all_schemes: Set[str] = set()
        self.scheme_variations: Dict[str, str] = {}  # variant -> canonical
        
        # Load schemes from Qdrant if client provided
        if qdrant_client:
            self._load_schemes_from_qdrant()
        else:
            logger.warning("No Qdrant client provided. Using LLM-only extraction.")
        
        logger.info(f"QueryDecomposer initialized with {len(self.all_schemes)} unique schemes")
    
    def _load_schemes_from_qdrant(self):
        """Load ALL scheme names from Qdrant collection"""
        try:
            logger.info(f"Loading scheme names from Qdrant collection: {self.collection_name}")
            
            # Scroll through all documents to get unique scheme names
            offset = None
            scheme_set = set()
            
            while True:
                results = self.qdrant_client.scroll(
                    collection_name=self.collection_name,
                    limit=100,
                    offset=offset,
                    with_payload=['scheme_name'],
                    with_vectors=False
                )
                
                points, offset = results
                
                if not points:
                    break
                
                # Extract scheme names
                for point in points:
                    scheme_name = point.payload.get('scheme_name')
                    if scheme_name and scheme_name != 'Unknown':
                        scheme_set.add(scheme_name)
                
                if offset is None:
                    break
            
            self.all_schemes = scheme_set
            
            # Build variations map for fuzzy matching
            self._build_variations_map()
            
            logger.info(f"Loaded {len(self.all_schemes)} unique schemes from Qdrant")
            
        except Exception as e:
            logger.error(f"Failed to load schemes from Qdrant: {e}")
            logger.warning("Falling back to LLM-only extraction")
            self.all_schemes = set()
    
    def _build_variations_map(self):
        """Build variations map for faster exact/fuzzy matching"""
        for scheme in self.all_schemes:
            # Store lowercase for case-insensitive matching
            self.scheme_variations[scheme.lower()] = scheme
            
            # Add common variations
            # Remove special characters
            clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', scheme)
            self.scheme_variations[clean_name.lower()] = scheme
            
            # Add acronym if applicable (e.g., "PMEGP" from "Prime Minister...")
            words = scheme.split()
            if len(words) > 2:
                acronym = ''.join(word[0].upper() for word in words if word[0].isupper())
                if len(acronym) >= 3:
                    self.scheme_variations[acronym.lower()] = scheme
        
        logger.debug(f"Built {len(self.scheme_variations)} scheme variations")
    
    def _extract_with_exact_match(self, query: str) -> List[str]:
        """Fast exact matching against scheme names (case-insensitive)"""
        found_schemes = set()
        query_lower = query.lower()
        
        for variant, canonical in self.scheme_variations.items():
            # Use word boundaries to avoid partial matches
            # Case-insensitive matching
            pattern = r'\b' + re.escape(variant) + r'\b'
            if re.search(pattern, query_lower, re.IGNORECASE):
                found_schemes.add(canonical)
                logger.debug(f"Exact match: '{variant}' -> {canonical}")
        
        return list(found_schemes)
    
    def _extract_with_fuzzy_match(self, query: str, threshold: int = 75) -> List[str]:
        """Fuzzy matching for handling typos and variations
        
        Lowered threshold from 85 to 75 to handle case variations better.
        
        Args:
            query: User query
            threshold: Minimum similarity score (0-100)
            
        Returns:
            List of matched scheme names
        """
        if not FUZZY_MATCHING_AVAILABLE or not self.all_schemes:
            return []
        
        try:
            # Extract potential scheme mentions (capitalized words/phrases + abbreviations)
            potential_schemes = re.findall(r'\b[A-Z][A-Za-z\s-]+\b|\b[A-Z]{3,}\b', query)
            
            found_schemes = set()
            
            for potential in potential_schemes:
                # Skip very short matches
                if len(potential) < 3:
                    continue
                
                # Fuzzy match against all schemes (case-insensitive)
                matches = process.extract(
                    potential.lower(),
                    [s.lower() for s in self.all_schemes],
                    scorer=fuzz.token_sort_ratio,
                    limit=3,
                    score_cutoff=threshold
                )
                
                for match_lower, score, _ in matches:
                    # Find original scheme name (case-preserved)
                    canonical = self.scheme_variations.get(match_lower)
                    if canonical:
                        found_schemes.add(canonical)
                        logger.debug(f"Fuzzy match: '{potential}' -> {canonical} (score: {score})")
            
            return list(found_schemes)
            
        except Exception as e:
            logger.warning(f"Fuzzy matching failed: {e}")
            return []
    
    def _extract_with_llm(self, query: str) -> List[str]:
        """LLM-based extraction with full scheme context"""
        # Build scheme examples from loaded schemes (sample for prompt)
        scheme_examples = list(self.all_schemes)[:50] if self.all_schemes else [
            "PMEGP", "MUDRA", "Stand Up India", "Startup India", "PM-KISAN"
        ]
        scheme_list_str = ", ".join(scheme_examples)
        if len(self.all_schemes) > 50:
            scheme_list_str += f" and {len(self.all_schemes) - 50} more schemes"
        
        prompt = PromptTemplate(
            template="""Extract government scheme names from the query.

Query: {query}

Available schemes include: {scheme_list}

Instructions:
1. Identify any government scheme names mentioned
2. Return ONLY the exact scheme names as they appear in the database
3. If no schemes found, return "NONE"
4. Separate multiple schemes with commas

Scheme names:""",
            input_variables=["query", "scheme_list"]
        )
        
        try:
            chain = prompt | self.llm
            response = chain.invoke({
                "query": query,
                "scheme_list": scheme_list_str
            })
            
            # Parse response
            result = response.content.strip()
            
            if result.upper() == "NONE" or not result:
                return []
            
            # Split by comma and clean
            extracted = [s.strip() for s in result.split(',')]
            
            # Validate against known schemes (fuzzy match)
            validated = []
            for scheme in extracted:
                # Try exact match first (case-insensitive)
                canonical = self.scheme_variations.get(scheme.lower())
                if canonical:
                    validated.append(canonical)
                    logger.debug(f"LLM extraction (exact): {scheme} -> {canonical}")
                # Try fuzzy match
                elif FUZZY_MATCHING_AVAILABLE and self.all_schemes:
                    matches = process.extractOne(
                        scheme.lower(),
                        [s.lower() for s in self.all_schemes],
                        scorer=fuzz.ratio,
                        score_cutoff=75  # Lowered from 85
                    )
                    if matches:
                        match_lower, score, _ = matches
                        canonical = self.scheme_variations.get(match_lower)
                        if canonical:
                            validated.append(canonical)
                            logger.debug(f"LLM extraction (fuzzy): '{scheme}' -> {canonical} (score: {score})")
            
            return validated
            
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")
            return []
    
    def extract_scheme_names(self, query: str) -> List[str]:
        """Extract scheme names using multi-stage approach
        
        Stages:
        1. Exact matching (fastest, case-insensitive)
        2. Fuzzy matching (handles variations, threshold=75)
        3. LLM extraction (fallback for complex cases)
        
        Args:
            query: User query
            
        Returns:
            List of detected scheme names
        """
        logger.info(f"Extracting scheme names from: '{query[:80]}...'")
        
        # Stage 1: Try exact matching first (fastest)
        exact_schemes = self._extract_with_exact_match(query)
        if exact_schemes:
            logger.info(f"Exact match found: {exact_schemes}")
            return exact_schemes
        
        # Stage 2: Try fuzzy matching
        if FUZZY_MATCHING_AVAILABLE:
            fuzzy_schemes = self._extract_with_fuzzy_match(query, threshold=75)
            if fuzzy_schemes:
                logger.info(f"Fuzzy match found: {fuzzy_schemes}")
                return fuzzy_schemes
        
        # Stage 3: Fallback to LLM for complex queries
        logger.debug("No direct matches, trying LLM extraction...")
        llm_schemes = self._extract_with_llm(query)
        
        if llm_schemes:
            logger.info(f"LLM extraction found: {llm_schemes}")
            return llm_schemes
        
        logger.info("No scheme names detected in query")
        return []
    
    def classify_query_type(self, query: str, detected_schemes: List[str]) -> Dict[str, any]:
        """Classify query type for routing decision"""
        has_scheme = len(detected_schemes) > 0
        
        classification = {
            'has_scheme': has_scheme,
            'schemes': detected_schemes,
            'retrieval_mode': 'filtered' if has_scheme else 'hybrid',
            'confidence': 1.0 if detected_schemes else 0.8
        }
        
        logger.info(
            f"Query classification: mode={classification['retrieval_mode']}, "
            f"schemes={detected_schemes}, confidence={classification['confidence']}"
        )
        
        return classification
    
    def decompose(self, query: str) -> Dict[str, any]:
        """Complete query decomposition pipeline"""
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
        """Build Qdrant filter parameters for scheme names"""
        if len(scheme_names) == 1:
            return {
                'must': [
                    {
                        'key': 'scheme_name',
                        'match': {'value': scheme_names[0]}
                    }
                ]
            }
        else:
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

def get_query_decomposer(qdrant_client=None, collection_name: str = None) -> QueryDecomposer:
    """Get or create global query decomposer instance"""
    global _query_decomposer
    if _query_decomposer is None:
        _query_decomposer = QueryDecomposer(qdrant_client, collection_name)
    return _query_decomposer


if __name__ == "__main__":
    # Test the query decomposer
    from qdrant_client import QdrantClient
    import config
    
    print("\n" + "="*80)
    print("DYNAMIC QUERY DECOMPOSER TEST (Case-Insensitive)")
    print("="*80 + "\n")
    
    # Initialize with Qdrant client
    client = QdrantClient(
        url=config.QDRANT_URL,
        api_key=config.QDRANT_API_KEY
    )
    
    decomposer = QueryDecomposer(client, config.COLLECTION_NAME)
    
    print(f"Loaded {len(decomposer.all_schemes)} schemes from Qdrant\n")
    print(f"Sample schemes: {list(decomposer.all_schemes)[:10]}\n")
    
    test_queries = [
        "Can women entrepreneurs apply for PMEGP?",  # Uppercase
        "What is the subsidy amount in Pmegp scheme?",  # Mixed case
        "Compare PMEGP and MUDRA schemes",  # Multiple schemes
        "What are the manufacturing subsidy schemes?",  # No specific scheme
        "How to apply for Pradhan Mantri MUDRA Yojana?",
        "CGTMSE loan guarantee eligibility criteria",
        "PM employement generation program benefits"  # Typo test
    ]
    
    for query in test_queries:
        print(f"Query: {query}")
        result = decomposer.decompose(query)
        print(f"  Detected: {result['detected_schemes']}")
        print(f"  Mode: {result['retrieval_mode']}")
        print(f"  Confidence: {result['confidence']}")
        print()
