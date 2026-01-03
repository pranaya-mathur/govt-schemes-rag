#!/usr/bin/env python3
"""Quick system test script for Government Schemes RAG"""

import sys
import time
from datetime import datetime

print("="*60)
print("Government Schemes RAG - System Test")
print("="*60)
print()

# Test 1: Check imports
print("[1/6] Testing imports...")
try:
    from src.llm import get_ollama_llm, get_groq_llm
    from src.retrieval import VectorRetriever
    from src.graph import app
    print("✅ All imports successful\n")
except Exception as e:
    print(f"❌ Import failed: {e}")
    print("\n⚠️  Fix: Ensure you've run 'pip install -r requirements.txt'\n")
    sys.exit(1)

# Test 2: Check Qdrant connection
print("[2/6] Testing Qdrant connection...")
try:
    retriever = VectorRetriever()
    print("✅ Qdrant connected successfully\n")
except Exception as e:
    print(f"❌ Qdrant connection failed: {e}")
    print("\n⚠️  Fix: Check QDRANT_URL and QDRANT_API_KEY in .env file\n")
    sys.exit(1)

# Test 3: Check Ollama
print("[3/6] Testing Ollama connection...")
try:
    ollama_llm = get_ollama_llm()
    test_response = ollama_llm.invoke("Say 'OK'")
    print("✅ Ollama connected successfully\n")
except Exception as e:
    print(f"❌ Ollama connection failed: {e}")
    print("\n⚠️  Fix: Ensure Ollama is running ('ollama serve')\n")
    sys.exit(1)

# Test 4: Check Groq
print("[4/6] Testing Groq connection...")
try:
    groq_llm = get_groq_llm()
    test_response = groq_llm.invoke("Say 'OK'")
    print("✅ Groq connected successfully\n")
except Exception as e:
    print(f"❌ Groq connection failed: {e}")
    print("\n⚠️  Fix: Check GROQ_API_KEY in .env file\n")
    sys.exit(1)

# Test 5: Test retrieval
print("[5/6] Testing document retrieval...")
try:
    test_query = "manufacturing schemes"
    docs = retriever.retrieve(test_query, top_k=3, intent="DISCOVERY")
    
    if len(docs) > 0:
        print(f"✅ Retrieved {len(docs)} documents")
        print(f"   Sample scheme: {docs[0]['payload'].get('scheme_name', 'N/A')}")
        print(f"   Score: {docs[0]['score']:.3f}\n")
    else:
        print("❌ No documents retrieved")
        print("\n⚠️  Fix: Ensure data pipeline has been run and Qdrant collection exists\n")
        sys.exit(1)
except Exception as e:
    print(f"❌ Retrieval failed: {e}")
    print("\n⚠️  Fix: Ensure data has been indexed to Qdrant\n")
    sys.exit(1)

# Test 6: Full RAG pipeline
print("[6/6] Testing complete RAG pipeline...")
print("   Query: 'What is PMEGP scheme?'")
print("   Please wait...\n")

try:
    start_time = time.time()
    result = app.invoke({"query": "What is PMEGP scheme?"})
    elapsed = time.time() - start_time
    
    print("✅ RAG pipeline completed successfully!\n")
    print(f"   Intent: {result.get('intent', 'Unknown')}")
    print(f"   Documents retrieved: {len(result.get('retrieved_docs', []))}")
    print(f"   Needed reflection: {result.get('needs_reflection', False)}")
    print(f"   Needed correction: {result.get('needs_correction', False)}")
    print(f"   Time taken: {elapsed:.2f}s\n")
    
    print("   Answer (first 200 chars):")
    answer = result.get('answer', 'No answer generated')
    print(f"   {answer[:200]}...\n")
    
except Exception as e:
    print(f"❌ RAG pipeline failed: {e}")
    print("\n⚠️  Check logs/rag_system.log for details\n")
    sys.exit(1)

# Success
print("="*60)
print("✅ ALL TESTS PASSED!")
print("="*60)
print()
print("Your system is ready! You can now:")
print("1. Start API: python -m uvicorn api.app:app --reload")
print("2. Visit Swagger: http://localhost:8000/docs")
print("3. Run custom tests with your own queries")
print()
print(f"Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()
