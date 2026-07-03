from datetime import datetime
from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    """Pydantic model representing a Document's metadata response."""
    id: str
    filename: str
    file_path: str
    file_type: str
    size: int
    checksum: str
    upload_date: datetime
    processing_status: str
    chunk_count: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReprocessRequest(BaseModel):
    """Pydantic model to customize chunking parameters during document reprocessing."""
    chunk_size: int = Field(default=1000, ge=100, le=10000, description="Size of text chunks in characters")
    chunk_overlap: int = Field(default=200, ge=0, le=5000, description="Overlapping characters between adjacent chunks")


class RetrievalRequest(BaseModel):
    """Pydantic model representing a similarity search query."""
    query: str = Field(..., min_length=1, description="The query string to search for")
    top_k: int = Field(default=4, ge=1, le=50, description="Number of results to return")
    document_id: str | None = Field(default=None, description="Optional document ID to restrict the search to")


class RetrievalChunk(BaseModel):
    """Pydantic model representing a single matched text segment from the vector store."""
    text: str
    document_id: str
    filename: str
    score: float
    chunk_index: int


class RetrievalResponse(BaseModel):
    """Pydantic model representing the overall retrieval results."""
    query: str
    results: list[RetrievalChunk]
