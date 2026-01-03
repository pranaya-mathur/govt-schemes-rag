from typing import TypedDict, List, Optional
from src.llm import get_ollama_llm, get_groq_llm
from src.prompts import (
    intent_prompt, relevance_prompt, reflection_prompt,
    answer_quality_prompt, corrective_prompt, answer_prompt
)
from src.retrieval import VectorRetriever
from src.exceptions import EmptyQueryError, InvalidIntentError, LLMError
from src.logger import setup_logger
import config

logger = setup_logger(__name__)

# Import iteration limits from config
MAX_REFLECTION_ITERATIONS = config.MAX_REFLECTION_ITERATIONS
MAX_CORRECTION_ITERATIONS = config.MAX_CORRECTION_ITERATIONS


class RAGState(TypedDict):
    query: str
    retrieved_docs: Optional[List[dict]]
    answer: Optional[str]
    needs_reflection: Optional[bool]
    needs_correction: Optional[bool]
    intent: Optional[str]
    reflection_count: Optional[int]
    correction_count: Optional[int]


# Hybrid LLM setup
ollama_llm = get_ollama_llm()  # For adaptive tasks (intent, reflection)
groq_llm = get_groq_llm()      # For heavy tasks (answer, judges)
retriever = VectorRetriever()


def classify_intent(query: str) -> str:
    """Classify user query intent using Ollama (deepseek-r1:8b)"""
    if not query or not query.strip():
        raise EmptyQueryError("Query cannot be empty")
    
    try:
        logger.info(f"Classifying intent for query: {query[:50]}...")
        chain = intent_prompt | ollama_llm  # Using Ollama
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
    """Intent classification node - Uses Ollama"""
    intent = classify_intent(state["query"])
    return {
        "intent": intent,
        "reflection_count": 0,
        "correction_count": 0
    }


def retrieval_node(state: RAGState):
    """Document retrieval node"""
    logger.info(f"Retrieving documents for query: {state['query'][:50]}...")
    docs = retriever.retrieve(state["query"])
    logger.info(f"Retrieved {len(docs)} documents")
    return {"retrieved_docs": docs}


def judge_relevance(query: str, retrieved_docs: list, reflection_count: int) -> bool:
    """Judge if retrieved docs are relevant using Groq (llama-3.3-70b)"""
    # Stop reflection if max iterations reached
    if reflection_count >= MAX_REFLECTION_ITERATIONS:
        logger.warning(f"Max reflection iterations ({MAX_REFLECTION_ITERATIONS}) reached. Proceeding with current docs.")
        return False
    
    try:
        schemes_text = retriever.format_for_judge(retrieved_docs)
        
        # DEBUG: Log what judge sees
        logger.debug(f"\n{'='*80}\nRELEVANCE JUDGE INPUT:\n{'='*80}\n"
                    f"Query: {query}\n\n"
                    f"Schemes Preview:\n{schemes_text[:1000]}...\n{'='*80}")
        
        chain = relevance_prompt | groq_llm  # Using Groq
        result = chain.invoke({"query": query, "schemes": schemes_text})
        
        # DEBUG: Log raw LLM response
        logger.debug(f"Relevance judge raw response: '{result.content}'")
        
        verdict = result.content.strip().upper()
        needs_reflection = verdict == "NO"
        
        logger.info(f"Relevance judgment: {verdict} → {'NEEDS_REFLECTION' if needs_reflection else 'RELEVANT'}")
        return needs_reflection
    except Exception as e:
        logger.error(f"Relevance judgment failed: {str(e)}")
        # Assume docs are relevant on error to avoid infinite loops
        return False


def selfrag_judge_node(state: RAGState):
    """Self-RAG relevance judgment node - Uses Groq"""
    reflection_count = state.get("reflection_count", 0)
    needs_reflection = judge_relevance(
        state["query"], 
        state["retrieved_docs"],
        reflection_count
    )
    return {"needs_reflection": needs_reflection}


def refine_query(query: str) -> str:
    """Refine query for better retrieval using Ollama (deepseek-r1:8b)"""
    try:
        logger.info(f"Refining query: {query[:50]}...")
        chain = reflection_prompt | ollama_llm  # Using Ollama
        result = chain.invoke({"query": query})
        refined = result.content.strip()
        logger.info(f"Refined query: {refined[:100]}...")
        return refined
    except Exception as e:
        logger.error(f"Query refinement failed: {str(e)}")
        # Return original query on failure
        return query


def reflection_node(state: RAGState):
    """Query refinement and re-retrieval node - Uses Ollama"""
    reflection_count = state.get("reflection_count", 0) + 1
    logger.info(f"Reflection iteration {reflection_count}/{MAX_REFLECTION_ITERATIONS}")
    
    refined_query = refine_query(state["query"])
    refined_docs = retriever.retrieve(refined_query)
    logger.info(f"Re-retrieved {len(refined_docs)} documents after refinement")
    
    return {
        "query": refined_query,
        "retrieved_docs": refined_docs,
        "needs_reflection": False,
        "needs_correction": False,
        "reflection_count": reflection_count
    }


def answer_node(state: RAGState):
    """Answer generation node - Uses Groq (llama-3.3-70b)"""
    try:
        logger.info("Generating answer...")
        schemes_text = retriever.format_for_answer(state["retrieved_docs"])
        
        # DEBUG: Log input to answer generation
        logger.debug(f"Answer generation using {len(state['retrieved_docs'])} documents")
        
        chain = answer_prompt | groq_llm  # Using Groq
        result = chain.invoke({
            "query": state["query"],
            "schemes": schemes_text
        })
        logger.info("Answer generated successfully")
        return {"answer": result.content}
    except Exception as e:
        logger.error(f"Answer generation failed: {str(e)}")
        raise LLMError(f"Failed to generate answer: {str(e)}")


def is_answer_inadequate(query: str, answer: str, correction_count: int) -> bool:
    """Check if answer quality is poor using Groq (llama-3.3-70b)"""
    # Stop correction if max iterations reached
    if correction_count >= MAX_CORRECTION_ITERATIONS:
        logger.warning(f"Max correction iterations ({MAX_CORRECTION_ITERATIONS}) reached. Accepting current answer.")
        return False
    
    try:
        # DEBUG: Log what quality judge sees
        logger.debug(f"\n{'='*80}\nQUALITY JUDGE INPUT:\n{'='*80}\n"
                    f"Query: {query}\n\n"
                    f"Answer:\n{answer[:500]}...\n{'='*80}")
        
        chain = answer_quality_prompt | groq_llm  # Using Groq
        result = chain.invoke({"query": query, "answer": answer})
        
        # DEBUG: Log raw LLM response
        logger.debug(f"Quality judge raw response: '{result.content}'")
        
        verdict = result.content.strip().upper()
        is_bad = verdict == "YES"
        
        logger.info(f"Answer quality check: {verdict} → {'INADEQUATE (needs correction)' if is_bad else 'GOOD (accepted)'}")
        return is_bad
    except Exception as e:
        logger.error(f"Answer quality check failed: {str(e)}")
        # Assume answer is good on error to avoid infinite loops
        return False


def corrective_query(query: str) -> str:
    """Generate corrective query using Ollama (deepseek-r1:8b)"""
    try:
        logger.info("Generating corrective query...")
        chain = corrective_prompt | ollama_llm  # Using Ollama
        result = chain.invoke({"query": query})
        corrected = result.content.strip()
        logger.info(f"Corrective query: {corrected[:100]}...")
        return corrected
    except Exception as e:
        logger.error(f"Corrective query generation failed: {str(e)}")
        return query


def corrective_rag_node(state: RAGState):
    """Corrective RAG node for answer improvement - Uses Ollama"""
    correction_count = state.get("correction_count", 0)
    
    needs_correction = is_answer_inadequate(
        state["query"], 
        state["answer"],
        correction_count
    )
    
    if not needs_correction:
        return {"needs_correction": False}
    
    correction_count += 1
    logger.info(f"Correction iteration {correction_count}/{MAX_CORRECTION_ITERATIONS}")
    
    new_query = corrective_query(state["query"])
    new_docs = retriever.retrieve(new_query)
    logger.info(f"Corrective retrieval returned {len(new_docs)} documents")
    
    return {
        "query": new_query,
        "retrieved_docs": new_docs,
        "needs_correction": False,
        "needs_reflection": False,
        "correction_count": correction_count
    }
