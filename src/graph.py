from langgraph.graph import StateGraph, END
from src.nodes import (
    RAGState,
    intent_node,
    retrieval_node,
    selfrag_judge_node,
    reflection_node,
    answer_node,
    corrective_rag_node
)


def route_after_selfrag(state: RAGState):
    """Route after self-RAG judgment"""
    return "reflection" if state.get("needs_reflection") else "answer"


def route_after_answer(state: RAGState):
    """Route after answer generation"""
    return "corrective" if state.get("needs_correction") else END


def build_graph():
    """Build and compile the RAG graph"""
    graph = StateGraph(RAGState)
    
    # Add nodes
    graph.add_node("intent", intent_node)
    graph.add_node("retrieve", retrieval_node)
    graph.add_node("selfrag", selfrag_judge_node)
    graph.add_node("reflection", reflection_node)
    graph.add_node("answer", answer_node)
    graph.add_node("corrective", corrective_rag_node)
    
    # Add edges
    graph.set_entry_point("intent")
    graph.add_edge("intent", "retrieve")
    graph.add_edge("retrieve", "selfrag")
    
    graph.add_conditional_edges(
        "selfrag",
        route_after_selfrag,
        {
            "reflection": "reflection",
            "answer": "answer"
        }
    )
    
    graph.add_edge("reflection", "selfrag")
    
    graph.add_conditional_edges(
        "answer",
        route_after_answer,
        {
            "corrective": "corrective",
            END: END
        }
    )
    
    graph.add_edge("corrective", "answer")
    
    return graph.compile()


# Global compiled graph
app = build_graph()
