#!/usr/bin/env python3
"""System integration test for RAG pipeline"""

import sys
import time
from datetime import datetime

print("=" * 60)
print("Government Schemes RAG - System Test")
print("=" * 60)
print()

# Test imports
print("[1/6] Checking imports...")
try:
    from src.llm import get_ollama_llm, get_groq_llm
    from src.retrieval import VectorRetriever
    from src.graph import app
    print("[PASS] All imports successful\n")
except Exception as e:
    print(f"[FAIL] Import error: {e}")
    print("\nFix: Run 'pip install -r requirements.txt'\n")
    sys.exit(1)

# Test Qdrant
print("[2/6] Checking Qdrant connection...")
try:
    retriever = VectorRetriever()
    print("[PASS] Connected to Qdrant\n")
except Exception as e:
    print(f"[FAIL] Qdrant error: {e}")
    print("\nFix: Verify QDRANT_URL and QDRANT_API_KEY in .env\n")
    sys.exit(1)

# Test Ollama
print("[3/6] Checking Ollama connection...")
try:
    ollama_llm = get_ollama_llm()
    response = ollama_llm.invoke("test")
    print("[PASS] Ollama is responding\n")
except Exception as e:
    print(f"[FAIL] Ollama error: {e}")
    print("\nFix: Start Ollama with 'ollama serve'\n")
    sys.exit(1)

# Test Groq
print("[4/6] Checking Groq API...")
try:
    groq_llm = get_groq_llm()
    response = groq_llm.invoke("test")
    print("[PASS] Groq API is working\n")
except Exception as e:
    print(f"[FAIL] Groq error: {e}")
    print("\nFix: Check GROQ_API_KEY in .env\n")
    sys.exit(1)

# Test retrieval
print("[5/6] Testing document retrieval...")
try:
    query = "manufacturing schemes"
    docs = retriever.retrieve(query, top_k=3, intent="DISCOVERY")
    
    if not docs:
        print("[FAIL] No documents found")
        print("\nFix: Run data pipeline to index documents\n")
        sys.exit(1)
    
    scheme_name = docs[0]['payload'].get('scheme_name', 'Unknown')
    score = docs[0]['score']
    print(f"[PASS] Retrieved {len(docs)} docs")
    print(f"       Top result: {scheme_name} (score: {score:.3f})\n")
except Exception as e:
    print(f"[FAIL] Retrieval error: {e}")
    print("\nFix: Ensure Qdrant collection exists\n")
    sys.exit(1)

# Test full pipeline
print("[6/6] Testing complete RAG pipeline...")
print("       Query: 'What is PMEGP scheme?'")
print("       Processing...\n")

try:
    start = time.time()
    result = app.invoke({"query": "What is PMEGP scheme?"})
    elapsed = time.time() - start
    
    print("[PASS] Pipeline completed\n")
    print(f"       Intent: {result.get('intent', 'N/A')}")
    print(f"       Documents: {len(result.get('retrieved_docs', []))}")
    print(f"       Self-RAG: {result.get('needs_reflection', False)}")
    print(f"       Corrective: {result.get('needs_correction', False)}")
    print(f"       Latency: {elapsed:.2f}s\n")
    
    answer = result.get('answer', 'No answer')
    print("       Answer preview:")
    print(f"       {answer[:180]}...\n")
    
except Exception as e:
    print(f"[FAIL] Pipeline error: {e}")
    print("\nCheck logs/rag_system.log for details\n")
    sys.exit(1)

print("=" * 60)
print("All tests passed successfully")
print("=" * 60)
print()
print("Next steps:")
print("  1. Start API: uvicorn api.app:app --reload")
print("  2. Visit: http://localhost:8000/docs")
print("  3. Try custom queries\n")
print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()
