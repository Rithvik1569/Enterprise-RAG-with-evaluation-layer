import os
import logging
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.embeddings import Embeddings
from app.config import settings

logger = logging.getLogger("rag_pipeline")


class MockEmbeddings(Embeddings):
    """Fallback mock embeddings when OpenAI API key is missing and sentence-transformers is unavailable."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        # Standard OpenAI 1536 dimension
        return [[0.1] * 1536 for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.1] * 1536


class VectorStoreManager:
    """Manages persistent ChromaDB vector store and embedding service initialization."""

    def __init__(self, persist_dir: str = settings.CHROMA_DIR):
        self.persist_dir = os.path.abspath(persist_dir)
        os.makedirs(self.persist_dir, exist_ok=True)
        self._embeddings = None

    def get_embeddings(self) -> Embeddings:
        """Initializes and returns the embedding provider based on config."""
        if self._embeddings is not None:
            return self._embeddings

        if settings.EMBEDDING_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
            logger.info("Using Gemini embeddings: %s", settings.EMBEDDING_MODEL)
            self._embeddings = GoogleGenerativeAIEmbeddings(
                google_api_key=settings.GEMINI_API_KEY,
                model=settings.EMBEDDING_MODEL
            )
        elif settings.EMBEDDING_PROVIDER == "openai" and settings.OPENAI_API_KEY:
            logger.info("Using OpenAI embeddings: %s", settings.EMBEDDING_MODEL)
            self._embeddings = OpenAIEmbeddings(
                openai_api_key=settings.OPENAI_API_KEY,
                model=settings.EMBEDDING_MODEL
            )
        else:
            try:
                # Try to use local HuggingFace embeddings
                logger.info("OpenAI API key missing or provider not set to openai. Trying HuggingFace embeddings...")
                from langchain_community.embeddings import HuggingFaceEmbeddings
                self._embeddings = HuggingFaceEmbeddings(
                    model_name="all-MiniLM-L6-v2"
                )
                logger.info("Successfully loaded local HuggingFace Embeddings (all-MiniLM-L6-v2)")
            except Exception as e:
                logger.warning(
                    "Failed to load HuggingFace embeddings (%s). Falling back to MockEmbeddings for development.",
                    str(e)
                )
                self._embeddings = MockEmbeddings()

        return self._embeddings

    def get_vectorstore(self, collection_name: str = "documents") -> Chroma:
        """Returns a persistent Chroma vector store instance."""
        embeddings = self.get_embeddings()
        suffix = settings.EMBEDDING_PROVIDER
        coll_name = f"{collection_name}_{suffix}"
        return Chroma(
            collection_name=coll_name,
            embedding_function=embeddings,
            persist_directory=self.persist_dir
        )

    def delete_document_chunks(self, document_id: str, collection_name: str = "documents") -> None:
        """Deletes all vector chunks belonging to a specific document ID."""
        try:
            vectorstore = self.get_vectorstore(collection_name)
            # Delete from chroma store matching document_id metadata
            vectorstore.delete(where={"document_id": document_id})
            logger.info("Deleted chunks for document_id %s from Chroma collection %s", document_id, collection_name)
        except Exception as e:
            logger.error("Failed to delete chunks for document %s from Chroma: %s", document_id, str(e))
            raise e
