from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from app.config import settings
from app.database import create_tables
from app.routers import auth as auth_router
from app.routers import admin as admin_router
from app.routers import documents as documents_router
from app.routers import retrieval as retrieval_router
from app.routers import chat as chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create DB tables. Shutdown: nothing needed (engine cleans up)."""
    await create_tables()
    yield


app = FastAPI(
    title="RAG AI Backend",
    description="FastAPI Backend for Retrieval-Augmented Generation Application",
    version="0.2.0",
    lifespan=lifespan,
)

@app.get("/")
async def root():
    """Redirect to API documentation."""
    return RedirectResponse(url="/docs")

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "backend": "FastAPI",
        "version": "0.2.0"
    }

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth_router.router)
app.include_router(admin_router.router)
app.include_router(documents_router.router)
app.include_router(retrieval_router.router)
app.include_router(chat_router.router)