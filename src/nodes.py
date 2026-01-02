from typing import TypedDict, List, Optional
from src.llm import get_llm
from src.prompts import (
    intent_prompt, relevance_prompt, reflection_prompt,
    answer_quality_prompt, corrective_prompt, answer_prompt
)
from src.retrieval import VectorRetriever
from src.exceptions import EmptyQueryError, InvalidIntentError, LLMError
from src.logger import setup_logger
import config

logger = setup_logger(__name__)


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
    if not query or not query.strip():
        raise EmptyQueryError("Query cannot be empty")
    
    try:
        logger.info(f"Classifying intent for query: {query[:50]}...")
        chain = intent_prompt | llm
        result = chain.invoke({"query": query})
        intent = result.content.strip().upper()
        
        if intent not in config.INTENT_LABELS:
            logger.warning(f"Unknown intent '{intent}', defaulting to GENERAL")
            intent = "GENERAL"
        
        logger.info(f"Classified intent: {intent}")
        return intent
    except Exception as e:
        logger.error(f"Intent classification failed: {str(e)}")
        raise InvalidIntentError(f"Failed to classify intent: {str(e)}")


def intent_node(state: RAGState):
    """Intent classification node"""
    intent = classify_intent(state["query"])
    return {"intent": intent}


def retrieval_node(state: RAGState):
    """Document retrieval node"""
    logger.info(f"Retrieving documents for query: {state['query'][:50]}...")
    docs = retriever.retrieve(state["query"])
    logger.info(f"Retrieved {len(docs)} documents")
    return {"retrieved_docs": docs}


def judge_relevance(query: str, retrieved_docs: list) -> bool:
    """Judge if retrieved docs are relevant"""
    try:
        schemes_text = retriever.format_for_judge(retrieved_docs)
        chain = relevance_prompt | llm
        result = chain.invoke({"query": query, "schemes": schemes_text})
        verdict = result.content.strip().upper()
        
        needs_reflection = verdict == "NO"
        logger.info(f"Relevance judgment: {'NEEDS_REFLECTION' if needs_reflection else 'RELEVANT'}")
        return needs_reflection
    except Exception as e:
        logger.error(f"Relevance judgment failed: {str(e)}")
        raise LLMError(f"Failed to judge relevance: {str(e)}")


def selfrag_judge_node(state: RAGState):
    """Self-RAG relevance judgment node"""
    needs_reflection = judge_relevance(
        state["query"], 
        state["retrieved_docs"]
    )
    return {"needs_reflection": needs_reflection}


def refine_query(query: str) -> str:
    """Refine query for better retrieval"""
    try:
        logger.info(f"Refining query: {query[:50]}...")
        chain = reflection_prompt | llm
        result = chain.invoke({"query": query})
        refined = result.content.strip()
        logger.info(f"Refined query: {refined[:50]}...")
        return refined
    except Exception as e:
        logger.error(f"Query refinement failed: {str(e)}")
        # Return original query on failure
        return query


def reflection_node(state: RAGState):
    """Query refinement and re-retrieval node"""
    refined_query = refine_query(state["query"])
    refined_docs = retriever.retrieve(refined_query)
    logger.info(f"Re-retrieved {len(refined_docs)} documents after refinement")
    
    return {
        "query": refined_query,
        "retrieved_docs": refined_docs,
        "needs_reflection": False,
        "needs_correction": False
    }


def answer_node(state: RAGState):
    """Answer generation node"""
    try:
        logger.info("Generating answer...")
        schemes_text = retriever.format_for_answer(state["retrieved_docs"])
        chain = answer_prompt | llm
        result = chain.invoke({
            "query": state["query"],
            "schemes": schemes_text
        })
        logger.info("Answer generated successfully")
        return {"answer": result.content}
    except Exception as e:
        logger.error(f"Answer generation failed: {str(e)}")
        raise LLMError(f"Failed to generate answer: {str(e)}")


def is_answer_inadequate(query: str, answer: str) -> bool:
    """Check if answer quality is poor"""
    try:
        chain = answer_quality_prompt | llm
        result = chain.invoke({"query": query, "answer": answer})
        verdict = result.content.strip().upper()
        
        is_bad = verdict == "YES"
        logger.info(f"Answer quality check: {'INADEQUATE' if is_bad else 'GOOD'}")
        return is_bad
    except Exception as e:
        logger.error(f"Answer quality check failed: {str(e)}")
        # Assume answer is good on error
        return False


def corrective_query(query: str) -> str:
    """Generate corrective query"""
    try:
        logger.info("Generating corrective query...")
        chain = corrective_prompt | llm
        result = chain.invoke({"query": query})
        corrected = result.content.strip()
        logger.info(f"Corrective query: {corrected[:50]}...")
        return corrected
    except Exception as e:
        logger.error(f"Corrective query generation failed: {str(e)}")
        return query


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
    logger.info(f"Corrective retrieval returned {len(new_docs)} documents")
    
    return {
        "query": new_query,
        "retrieved_docs": new_docs,
        "needs_correction": False,
        "needs_reflection": False
    }
