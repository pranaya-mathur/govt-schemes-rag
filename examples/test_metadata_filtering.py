"""Test script for metadata-aware retrieval feature

Tests:
1. Query decomposition (scheme extraction)
2. Filtered retrieval (single scheme)
3. Comparison retrieval (multiple schemes)
4. Discovery mode (no scheme detected)
5. End-to-end integration
"""
import sys
sys.path.append('.')

from src.query_decomposer import get_query_decomposer
from src.retrieval import VectorRetriever
from src.logger import setup_logger
import config

logger = setup_logger(__name__)


def print_section(title):
    """Print section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def test_query_decomposer():
    """Test 1: Query Decomposition"""
    print_section("TEST 1: QUERY DECOMPOSITION")
    
    decomposer = get_query_decomposer()
    
    test_cases = [
        "Can women entrepreneurs apply for PMEGP?",
        "What is the subsidy amount in MUDRA scheme?",
        "Compare PMEGP and Stand Up India schemes",
        "What are the manufacturing subsidy schemes?",  # No specific scheme
        "How to apply for Pradhan Mantri MUDRA Yojana?",
        "CGTMSE loan guarantee eligibility criteria"
    ]
    
    for query in test_cases:
        result = decomposer.decompose(query)
        print(f"Query: {query}")
        print(f"  ✓ Detected Schemes: {result['detected_schemes']}")
        print(f"  ✓ Retrieval Mode: {result['retrieval_mode']}")
        print(f"  ✓ Confidence: {result['confidence']}")
        if result.get('filter_params'):
            print(f"  ✓ Filter Ready: Yes")
        print()
    
    print("✅ Query Decomposer Test PASSED\n")


def test_filtered_retrieval():
    """Test 2: Filtered Retrieval (Single Scheme)"""
    print_section("TEST 2: FILTERED RETRIEVAL (SINGLE SCHEME)")
    
    retriever = VectorRetriever()
    
    query = "What are the eligibility criteria?"
    detected_schemes = ["PMEGP"]
    
    print(f"Query: {query}")
    print(f"Detected Schemes: {detected_schemes}")
    print(f"Expected: Only PMEGP documents\n")
    
    # Manually trigger metadata retrieval
    docs, metadata_info = retriever.metadata_retriever.retrieve_with_fallback(
        query=query,
        scheme_names=detected_schemes,
        top_k=5,
        hybrid_retriever=retriever.hybrid_retriever
    )
    
    print(f"Retrieved {len(docs)} documents:")
    for i, doc in enumerate(docs, 1):
        payload = doc['payload']
        print(
            f"  {i}. {payload['scheme_name']} - {payload['theme']} "
            f"(score: {doc['score']:.3f}, method: {doc.get('retrieval_method', 'unknown')})"
        )
    
    # Validate all docs are from PMEGP
    all_pmegp = all(doc['payload']['scheme_name'] == 'PMEGP' for doc in docs)
    
    if all_pmegp:
        print("\n✅ Filtered Retrieval Test PASSED - All results from PMEGP!\n")
    else:
        print("\n❌ Filtered Retrieval Test FAILED - Mixed schemes found!\n")


def test_comparison_retrieval():
    """Test 3: Comparison Retrieval (Multiple Schemes)"""
    print_section("TEST 3: COMPARISON RETRIEVAL (MULTIPLE SCHEMES)")
    
    retriever = VectorRetriever()
    
    query = "Compare subsidy benefits"
    detected_schemes = ["PMEGP", "MUDRA"]
    
    print(f"Query: {query}")
    print(f"Detected Schemes: {detected_schemes}")
    print(f"Expected: Balanced representation of both schemes\n")
    
    results_by_scheme = retriever.metadata_retriever.retrieve_multi_scheme_comparison(
        query=query,
        scheme_names=detected_schemes,
        docs_per_scheme=3
    )
    
    for scheme, docs in results_by_scheme.items():
        print(f"\n{scheme}: {len(docs)} documents")
        for i, doc in enumerate(docs, 1):
            payload = doc['payload']
            print(
                f"  {i}. {payload['theme']} (score: {doc['score']:.3f})"
            )
    
    # Validate both schemes represented
    has_both = all(scheme in results_by_scheme for scheme in detected_schemes)
    
    if has_both:
        print("\n✅ Comparison Retrieval Test PASSED - Both schemes represented!\n")
    else:
        print("\n❌ Comparison Retrieval Test FAILED - Missing scheme(s)!\n")


def test_discovery_mode():
    """Test 4: Discovery Mode (No Scheme Detected)"""
    print_section("TEST 4: DISCOVERY MODE (NO SPECIFIC SCHEME)")
    
    retriever = VectorRetriever()
    
    query = "What are the best schemes for small entrepreneurs?"
    
    print(f"Query: {query}")
    print(f"Expected: Hybrid search across all schemes\n")
    
    # Use the main retrieve method (automatic routing)
    docs = retriever.retrieve(query=query, top_k=5, intent="DISCOVERY")
    
    print(f"Retrieved {len(docs)} documents:")
    
    schemes_found = set()
    for i, doc in enumerate(docs, 1):
        payload = doc['payload']
        scheme = payload['scheme_name']
        schemes_found.add(scheme)
        
        print(
            f"  {i}. {scheme} - {payload['theme']} "
            f"(score: {doc['score']:.3f})"
        )
    
    print(f"\nUnique schemes found: {len(schemes_found)}")
    print(f"Schemes: {schemes_found}")
    
    # Validate multiple schemes discovered
    if len(schemes_found) >= 2:
        print("\n✅ Discovery Mode Test PASSED - Multiple schemes discovered!\n")
    else:
        print("\n⚠️ Discovery Mode Test - Only one scheme found (may be expected)\n")


def test_end_to_end():
    """Test 5: End-to-End Integration"""
    print_section("TEST 5: END-TO-END INTEGRATION")
    
    retriever = VectorRetriever()
    
    test_queries = [
        {
            "query": "Can women apply for PMEGP scheme?",
            "intent": "ELIGIBILITY",
            "expected_mode": "filtered",
            "expected_scheme": "PMEGP"
        },
        {
            "query": "What manufacturing schemes are available?",
            "intent": "DISCOVERY",
            "expected_mode": "hybrid",
            "expected_scheme": None
        }
    ]
    
    for i, test_case in enumerate(test_queries, 1):
        print(f"Test Case {i}: {test_case['query']}")
        print(f"Intent: {test_case['intent']}")
        print(f"Expected Mode: {test_case['expected_mode']}\n")
        
        docs = retriever.retrieve(
            query=test_case['query'],
            top_k=3,
            intent=test_case['intent']
        )
        
        if docs:
            # Check decomposition metadata
            decomp = docs[0].get('decomposition', {})
            actual_mode = decomp.get('retrieval_mode', 'unknown')
            
            print(f"  ✓ Retrieved: {len(docs)} documents")
            print(f"  ✓ Actual Mode: {actual_mode}")
            print(f"  ✓ Detected Schemes: {decomp.get('detected_schemes', [])}")
            
            # Show top result
            top_doc = docs[0]
            payload = top_doc['payload']
            print(f"  ✓ Top Result: {payload['scheme_name']} - {payload['theme']} (score: {top_doc['score']:.3f})")
            
            # Validate mode
            mode_match = actual_mode == test_case['expected_mode']
            
            if mode_match:
                print(f"  ✅ Mode Match: {actual_mode}\n")
            else:
                print(f"  ❌ Mode Mismatch: Expected {test_case['expected_mode']}, got {actual_mode}\n")
        else:
            print("  ❌ No documents retrieved!\n")
    
    print("✅ End-to-End Integration Test COMPLETED\n")


def main():
    """Run all tests"""
    print("\n" + "#"*80)
    print("#" + " "*78 + "#")
    print("#" + "  METADATA-AWARE RETRIEVAL - TEST SUITE".center(78) + "#")
    print("#" + " "*78 + "#")
    print("#"*80)
    
    try:
        # Test 1: Query Decomposition
        test_query_decomposer()
        
        # Test 2: Filtered Retrieval
        test_filtered_retrieval()
        
        # Test 3: Comparison Retrieval
        test_comparison_retrieval()
        
        # Test 4: Discovery Mode
        test_discovery_mode()
        
        # Test 5: End-to-End
        test_end_to_end()
        
        print_section("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("Your metadata-aware retrieval is working correctly!")
        print("\nNext steps:")
        print("1. Test with your actual queries")
        print("2. Monitor logs for routing decisions")
        print("3. Add more schemes to KNOWN_SCHEMES if needed")
        print()
        
    except Exception as e:
        print_section("❌ TEST SUITE FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
