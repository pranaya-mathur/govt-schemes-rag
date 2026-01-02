#!/usr/bin/env python3
from src.graph import app


def query_schemes(user_query: str):
    """Query the RAG system"""
    response = app.invoke({"query": user_query})
    return response["answer"]


if __name__ == "__main__":
    # Example queries
    queries = [
        "subsidy schemes for small entrepreneurs",
        "how much money is given under CISS",
        "who is eligible for MSME schemes",
        "compare MSME and startup subsidy schemes",
        "how to apply for government schemes"
    ]
    
    print("=" * 60)
    print("Government Schemes RAG System")
    print("=" * 60)
    
    for query in queries:
        print(f"\n\nQuery: {query}")
        print("-" * 60)
        answer = query_schemes(query)
        print(answer)
