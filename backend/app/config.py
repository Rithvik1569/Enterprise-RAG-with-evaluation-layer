import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    ENVIRONMENT: str = "development"

    # LLM keys (optional initially)
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""

    # Database (SQLite by default — swap to postgresql+asyncpg:// for production)
    DATABASE_URL: str = "sqlite+aiosqlite:///./ragdb.sqlite"

    # JWT Auth
    SECRET_KEY: str = "change-this-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Document Upload & Ingestion Settings
    UPLOAD_DIR: str = "./uploads"
    CHROMA_DIR: str = "./chromadb_store"
    EMBEDDING_PROVIDER: str = "openai"  # openai or local
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # Allow loading from backend/.env file
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
