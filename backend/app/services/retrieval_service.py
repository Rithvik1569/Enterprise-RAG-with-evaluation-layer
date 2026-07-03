import logging
from app.storage.vector_store import VectorStoreManager
from app.schemas.document import RetrievalChunk

logger = logging.getLogger("rag_pipeline")


class RetrievalService:
    """Handles vector search queries and formats matched chunks with relevance scores."""

    def __init__(self):
        self.vector_manager = VectorStoreManager()

    async def retrieve(
        self,
        query: str,
        top_k: int = 4,
        document_id: str | None = None,
    ) -> list[RetrievalChunk]:
        """Queries ChromaDB vector index and returns similarity matched chunks."""
        vectorstore = self.vector_manager.get_vectorstore()
        
        # Define filter if document_id is provided
        search_filter = None
        if document_id:
            search_filter = {"document_id": document_id}

        logger.info("Executing retrieval search: query='%s', top_k=%d, filter=%s", query, top_k, search_filter)

        # Retrieve documents with relevance scores
        results = vectorstore.similarity_search_with_score(
            query,
            k=top_k,
            filter=search_filter,
        )

        retrieved_chunks = []
        for doc, score in results:
            retrieved_chunks.append(
                RetrievalChunk(
                    text=doc.page_content,
                    document_id=doc.metadata.get("document_id", ""),
                    filename=doc.metadata.get("filename", ""),
                    chunk_index=int(doc.metadata.get("chunk_index", 0)),
                    score=float(score),
                )
            )

        return retrieved_chunks
