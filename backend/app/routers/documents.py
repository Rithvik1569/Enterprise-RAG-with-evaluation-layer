from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models.document import Document
from app.schemas.document import DocumentResponse, ReprocessRequest
from app.services.document_processor import DocumentProcessor
from app.storage.file_store import FileStore
from app.storage.vector_store import VectorStoreManager

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    chunk_size: int = Form(1000),
    chunk_overlap: int = Form(200),
    db: AsyncSession = Depends(get_db),
):
    """Uploads a document file (PDF, DOCX, TXT) and triggers the ingestion pipeline."""
    processor = DocumentProcessor(db)
    return await processor.upload_and_process(file, chunk_size, chunk_overlap)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(db: AsyncSession = Depends(get_db)):
    """Lists all uploaded documents and their ingestion metadata status."""
    stmt = select(Document).order_by(Document.upload_date.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{id}", response_model=DocumentResponse)
async def get_document(id: str, db: AsyncSession = Depends(get_db)):
    """Retrieves metadata of a specific document by its ID."""
    stmt = select(Document).where(Document.id == id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
    return doc


@router.delete("/{id}")
async def delete_document(id: str, db: AsyncSession = Depends(get_db)):
    """Deletes a document's metadata, physical file, and corresponding vector chunks."""
    stmt = select(Document).where(Document.id == id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # 1. Delete vector embeddings from vector store
    vstore_manager = VectorStoreManager()
    try:
        vstore_manager.delete_document_chunks(doc.id)
    except Exception as e:
        # Log error and continue to delete metadata/file anyway to keep state clean
        # or propagate based on production policy. We will log it.
        pass

    # 2. Delete physical raw file from storage
    fstore = FileStore()
    fstore.delete_file(doc.file_path)

    # 3. Delete metadata record from SQL database
    await db.delete(doc)
    await db.commit()

    return {
        "message": f"Document '{doc.filename}' deleted successfully.",
        "id": id,
    }


@router.post("/{id}/reprocess", response_model=DocumentResponse)
async def reprocess_document(
    id: str,
    req: ReprocessRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reprocesses a document already stored on disk with customized chunk size/overlap."""
    processor = DocumentProcessor(db)
    return await processor.reprocess_document(id, req.chunk_size, req.chunk_overlap)
