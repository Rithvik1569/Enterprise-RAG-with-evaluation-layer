from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# SQLite needs check_same_thread=False; PostgreSQL ignores connect_args
_connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

# Create the async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    connect_args=_connect_args,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields a database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    """Create all tables on startup (auto-creates SQLite file if needed)."""
    async with engine.begin() as conn:
        # Import models so metadata is populated
        from app.models import User, Document, Evaluation  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
