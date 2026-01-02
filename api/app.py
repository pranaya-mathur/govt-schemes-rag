from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from api.models import QueryRequest, QueryResponse, DocumentResponse, HealthResponse
from src.graph import app as rag_app
from src.retrieval import VectorRetriever
from src.exceptions import RAGException
from src.logger import setup_logger

logger = setup_logger(__name__)

app = FastAPI(
    title="Government Schemes RAG API",
    description="Multi-agent RAG system for Indian government schemes",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Government Schemes RAG API",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    try:
        retriever = VectorRetriever()
        qdrant_connected = True
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        qdrant_connected = False
    
    return HealthResponse(
        status="healthy" if qdrant_connected else "degraded",
        version="1.0.0",
        qdrant_connected=qdrant_connected
    )


@app.post("/query", response_model=QueryResponse, tags=["RAG"])
async def query_schemes(request: QueryRequest):
    """Query government schemes"""
    try:
        logger.info(f"Received query: {request.query}")
        
        # Run RAG pipeline
        result = rag_app.invoke({
            "query": request.query
        })
        
        # Format response
        docs = []
        for doc in result.get("retrieved_docs", []):
            payload = doc["payload"]
            docs.append(DocumentResponse(
                id=str(doc["id"]),
                score=doc["score"],
                scheme_name=payload.get("scheme_name", "Unknown"),
                theme=payload.get("theme", "Unknown"),
                text=payload.get("text", ""),
                official_url=payload.get("official_url")
            ))
        
        response = QueryResponse(
            query=result.get("query", request.query),
            intent=result.get("intent", "GENERAL"),
            answer=result.get("answer", ""),
            retrieved_docs=docs[:request.top_k],
            needs_reflection=result.get("needs_reflection", False),
            needs_correction=result.get("needs_correction", False)
        )
        
        logger.info(f"Query processed successfully. Intent: {response.intent}")
        return response
        
    except RAGException as e:
        logger.error(f"RAG error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG processing failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.exception_handler(RAGException)
async def rag_exception_handler(request, exc):
    """Handle RAG exceptions"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc)}
    )


if __name__ == "__main__":
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
