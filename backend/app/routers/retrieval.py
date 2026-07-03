from fastapi import APIRouter
from app.schemas.document import RetrievalRequest, RetrievalResponse
from app.services.retrieval_service import RetrievalService

router = APIRouter(prefix="/api/retrieval", tags=["retrieval"])


@router.post("/search", response_model=RetrievalResponse)
async def search(req: RetrievalRequest):
    """Performs similarity search in the vector database with metadata filtering support."""
    retrieval_service = RetrievalService()
    results = await retrieval_service.retrieve(
        query=req.query,
        top_k=req.top_k,
        document_id=req.document_id,
    )
    return RetrievalResponse(query=req.query, results=results)
