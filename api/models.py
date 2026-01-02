from pydantic import BaseModel, Field
from typing import Optional, List


class QueryRequest(BaseModel):
    """Request model for query endpoint"""
    query: str = Field(..., min_length=1, description="User query")
    top_k: Optional[int] = Field(5, ge=1, le=20, description="Number of docs to retrieve")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "subsidy schemes for small entrepreneurs",
                "top_k": 5
            }
        }


class DocumentResponse(BaseModel):
    """Retrieved document model"""
    id: str
    score: float
    scheme_name: str
    theme: str
    text: str
    official_url: Optional[str]


class QueryResponse(BaseModel):
    """Response model for query endpoint"""
    query: str
    intent: str
    answer: str
    retrieved_docs: List[DocumentResponse]
    needs_reflection: bool
    needs_correction: bool
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "subsidy schemes for small entrepreneurs",
                "intent": "DISCOVERY",
                "answer": "Here are the relevant subsidy schemes...",
                "retrieved_docs": [
                    {
                        "id": "123",
                        "score": 0.87,
                        "scheme_name": "PMEGP",
                        "theme": "benefits",
                        "text": "Prime Minister's Employment Generation Programme...",
                        "official_url": "https://www.kviconline.gov.in/pmegp"
                    }
                ],
                "needs_reflection": False,
                "needs_correction": False
            }
        }


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    qdrant_connected: bool
