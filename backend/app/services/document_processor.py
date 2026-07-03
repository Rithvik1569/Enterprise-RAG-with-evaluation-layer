import os
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import UploadFile, HTTPException, status
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LC_Document

from app.config import settings
from app.models.document import Document
from app.storage.file_store import FileStore
from app.storage.vector_store import VectorStoreManager
from app.services.text_extractor import TextExtractor
from app.services.text_cleaner import TextCleaner

logger = logging.getLogger("rag_pipeline")


class DocumentProcessor:
    """Orchestrates the document ingestion pipeline:
    Save file -> Extract text -> Clean -> Chunk -> Embed & Index -> Update Metadata DB
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.file_store = FileStore()
        self.vector_manager = VectorStoreManager()

    async def upload_and_process(
        self,
        file: UploadFile,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
    ) -> Document:
        """Validates, stores, and indexes a newly uploaded document."""
        filename = file.filename
        file_type = os.path.splitext(filename)[1].lower().strip(".")
        if file_type not in ["pdf", "docx", "txt"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {file_type}. Supported types: PDF, DOCX, TXT.",
            )

        # 1. Save as temporary file to calculate checksum and prevent duplicates
        temp_filename = f"temp_{filename}"
        temp_path = await self.file_store.save_file(file, temp_filename)
        checksum = self.file_store.compute_checksum(temp_path)

        # 2. Check duplicate uploads via checksum
        stmt = select(Document).where(Document.checksum == checksum)
        result = await self.db.execute(stmt)
        existing_doc = result.scalar_one_or_none()
        if existing_doc:
            self.file_store.delete_file(temp_path)
            # Return or raise duplicate alert
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Duplicate upload: '{filename}' has the exact same content as already existing document '{existing_doc.filename}' (ID: {existing_doc.id}).",
            )

        # 3. Rename to permanent filepath
        perm_filename = f"{checksum}_{filename}"
        perm_path = self.file_store.get_file_path(perm_filename)
        
        # If perm file already exists for some reason, delete temp and use perm
        if os.path.exists(perm_path):
            self.file_store.delete_file(temp_path)
        else:
            os.rename(temp_path, perm_path)

        file_size = os.path.getsize(perm_path)

        # 4. Insert metadata record with 'processing' status
        db_doc = Document(
            filename=filename,
            file_path=perm_path,
            file_type=file_type,
            size=file_size,
            checksum=checksum,
            processing_status="processing",
            chunk_count=0,
        )
        self.db.add(db_doc)
        await self.db.commit()
        await self.db.refresh(db_doc)

        # 5. Run the processing pipeline
        try:
            await self._run_pipeline(db_doc, chunk_size, chunk_overlap)
        except Exception as e:
            logger.exception("Ingestion pipeline failed for document: %s", db_doc.id)
            db_doc.processing_status = "failed"
            db_doc.error_message = str(e)
            db_doc.updated_at = datetime.now(timezone.utc)
            await self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Ingestion pipeline failed: {str(e)}",
            )

        return db_doc

    async def reprocess_document(
        self,
        doc_id: str,
        chunk_size: int,
        chunk_overlap: int,
    ) -> Document:
        """Reprocesses an existing document with new chunking configurations."""
        stmt = select(Document).where(Document.id == doc_id)
        result = await self.db.execute(stmt)
        db_doc = result.scalar_one_or_none()
        if not db_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document metadata record not found.",
            )

        if not os.path.exists(db_doc.file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Raw file has been deleted from disk. Cannot reprocess.",
            )

        # Clean up existing vector store chunks first
        self.vector_manager.delete_document_chunks(db_doc.id)

        # Reset metadata status
        db_doc.processing_status = "processing"
        db_doc.error_message = None
        db_doc.chunk_count = 0
        db_doc.updated_at = datetime.now(timezone.utc)
        await self.db.commit()

        # Run pipeline
        try:
            await self._run_pipeline(db_doc, chunk_size, chunk_overlap)
        except Exception as e:
            logger.exception("Reprocessing pipeline failed for document: %s", db_doc.id)
            db_doc.processing_status = "failed"
            db_doc.error_message = str(e)
            db_doc.updated_at = datetime.now(timezone.utc)
            await self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Reprocessing failed: {str(e)}",
            )

        return db_doc

    async def _run_pipeline(self, db_doc: Document, chunk_size: int, chunk_overlap: int):
        """Internal helper to execute text extraction, cleaning, chunking, and embedding."""
        # A. Extract text
        raw_text = TextExtractor.extract(db_doc.file_path, db_doc.file_type)

        # B. Clean text
        cleaned_text = TextCleaner.clean(raw_text)

        # C. Chunk text
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
        chunks = splitter.split_text(cleaned_text)

        if not chunks:
            raise ValueError("Document yielded no text chunks after splitting.")

        # D. Add to vector store
        lc_docs = []
        for idx, chunk in enumerate(chunks):
            lc_docs.append(
                LC_Document(
                    page_content=chunk,
                    metadata={
                        "document_id": db_doc.id,
                        "filename": db_doc.filename,
                        "chunk_index": idx,
                    },
                )
            )

        vectorstore = self.vector_manager.get_vectorstore()
        vectorstore.add_documents(lc_docs)

        # E. Update record status
        db_doc.processing_status = "completed"
        db_doc.chunk_count = len(chunks)
        db_doc.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(db_doc)
