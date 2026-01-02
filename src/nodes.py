from typing import TypedDict, List, Optional
from src.llm import get_llm
from src.prompts import (
    intent_prompt, relevance_prompt, reflection_prompt,
    answer_quality_prompt, corrective_prompt, answer_prompt
)
from src.retrieval import VectorRetriever
import config


class RAGState(TypedDict):
    query: str
    retrieved_docs: Optional[List[dict]]
    answer: Optional[str]
    needs_reflection: Optional[bool]
    needs_correction: Optional[bool]
    intent: Optional[str]


llm = get_llm()
retriever = VectorRetriever()


def classify_intent(query: str) -> str:
    """Classify user query intent"""
    chain = intent_prompt | llm
    result = chain.invoke({"query": query})
    intent = result.content.strip().upper()
    
    if intent not in config.INTENT_LABELS:
        intent = "GENERAL"
    
    return intent


def intent_node(state: RAGState):
    """Intent classification node"""
    intent = classify_intent(state["query"])
    return {"intent": intent}


def retrieval_node(state: RAGState):
    """Document retrieval node"""
    docs = retriever.retrieve(state["query"])
    return {"retrieved_docs": docs}


def judge_relevance(query: str, retrieved_docs: list) -> bool:
    """Judge if retrieved docs are relevant"""
    schemes_text = retriever.format_for_judge(retrieved_docs)
    chain = relevance_prompt | llm
    result = chain.invoke({"query": query, "schemes": schemes_text})
    verdict = result.content.strip().upper()
    return verdict == "NO"  # needs_reflection if NO


def selfrag_judge_node(state: RAGState):
    """Self-RAG relevance judgment node"""
    needs_reflection = judge_relevance(
        state["query"], 
        state["retrieved_docs"]
    )
    return {"needs_reflection": needs_reflection}


def refine_query(query: str) -> str:
    """Refine query for better retrieval"""
    chain = reflection_prompt | llm
    result = chain.invoke({"query": query})
    return result.content.strip()


def reflection_node(state: RAGState):
    """Query refinement and re-retrieval node"""
    refined_query = refine_query(state["query"])
    refined_docs = retriever.retrieve(refined_query)
    
    return {
        "query": refined_query,
        "retrieved_docs": refined_docs,
        "needs_reflection": False,
        "needs_correction": False
    }


def answer_node(state: RAGState):
    """Answer generation node"""
    schemes_text = retriever.format_for_answer(state["retrieved_docs"])
    chain = answer_prompt | llm
    result = chain.invoke({
        "query": state["query"],
        "schemes": schemes_text
    })
    return {"answer": result.content}


def is_answer_inadequate(query: str, answer: str) -> bool:
    """Check if answer quality is poor"""
    chain = answer_quality_prompt | llm
    result = chain.invoke({"query": query, "answer": answer})
    verdict = result.content.strip().upper()
    return verdict == "YES"


def corrective_query(query: str) -> str:
    """Generate corrective query"""
    chain = corrective_prompt | llm
    result = chain.invoke({"query": query})
    return result.content.strip()


def corrective_rag_node(state: RAGState):
    """Corrective RAG node for answer improvement"""
    needs_correction = is_answer_inadequate(
        state["query"], 
        state["answer"]
    )
    
    if not needs_correction:
        return {"needs_correction": False}
    
    new_query = corrective_query(state["query"])
    new_docs = retriever.retrieve(new_query)
    
    return {
        "query": new_query,
        "retrieved_docs": new_docs,
        "needs_correction": False,
        "needs_reflection": False
    }
