from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status

from app.database.mongo import get_db
from app.models.document import DocumentResponse
from app.models.document import ReprocessRequest
from app.services.rag_service import DocumentProcessor
from app.utils.file_store import FileStore
from app.utils.vector_store import VectorStoreManager

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    chunk_size: int = Form(1000),
    chunk_overlap: int = Form(200),
    db = Depends(get_db),
):
    """Uploads a document file (PDF, DOCX, TXT) and triggers the ingestion pipeline."""
    processor = DocumentProcessor(db)
    return await processor.upload_and_process(file, chunk_size, chunk_overlap)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(db = Depends(get_db)):
    """Lists all uploaded documents and their ingestion metadata status."""
    cursor = db["documents"].find().sort("upload_date", -1)
    docs = await cursor.to_list(length=1000)
    return [DocumentResponse(**doc) for doc in docs]


@router.get("/{id}", response_model=DocumentResponse)
async def get_document(id: str, db = Depends(get_db)):
    """Retrieves metadata of a specific document by its ID."""
    doc = await db["documents"].find_one({"_id": id})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
    return DocumentResponse(**doc)


@router.delete("/{id}")
async def delete_document(id: str, db = Depends(get_db)):
    """Deletes a document's metadata, physical file, and corresponding vector chunks."""
    doc = await db["documents"].find_one({"_id": id})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # 1. Delete vector embeddings from vector store
    vstore_manager = VectorStoreManager()
    try:
        vstore_manager.delete_document_chunks(id)
    except Exception as e:
        # Log error and continue to delete metadata/file anyway to keep state clean
        # or propagate based on production policy. We will log it.
        pass

    # 2. Delete physical raw file from storage
    fstore = FileStore()
    fstore.delete_file(doc["file_path"])

    # 3. Delete metadata record from SQL database
    await db["documents"].delete_one({"_id": id})

    return {
        "message": f"Document '{doc['filename']}' deleted successfully.",
        "id": id,
    }


@router.post("/{id}/reprocess", response_model=DocumentResponse)
async def reprocess_document(
    id: str,
    req: ReprocessRequest,
    db = Depends(get_db),
):
    """Reprocesses a document already stored on disk with customized chunk size/overlap."""
    processor = DocumentProcessor(db)
    return await processor.reprocess_document(id, req.chunk_size, req.chunk_overlap)
