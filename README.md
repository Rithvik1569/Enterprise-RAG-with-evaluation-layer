# Enterprise RAG SaaS System

Enterprise RAG is a production-ready, enterprise-grade Retrieval-Augmented Generation (RAG) SaaS platform. It combines real-time grounding search with an automated evaluation layer (faithfulness, relevance, precision, recall) and a modern admin analytics suite.

---

## Technical Stack & Architecture

- **Frontend**: React (v19) + TypeScript + Vite + Tailwind CSS (v4)
- **Backend**: FastAPI + SQLAlchemy (v2.0)
- **Database**: PostgreSQL (Production) / SQLite (Development) + Alembic migrations
- **Vector Database**: ChromaDB
- **Evaluation Engine**: Parallel prompt evaluations modeled after DeepEval & Ragas scoring definitions
- **Deployment**: Docker + Docker Compose + Nginx proxying

---

## Directory Structure

```text
Final AI project/
├── docker-compose.yml          # Full-stack orchestrator
├── backend/
│   ├── app/
│   │   ├── models/            # SQLAlchemy database schemas
│   │   ├── routers/           # FastAPI routers (chat, documents, admin, auth)
│   │   ├── schemas/           # Pydantic serialization models
│   │   ├── services/          # RAG indexers, LLM client, EvaluationService
│   │   ├── main.py            # API Server lifespan and routers registration
│   │   └── database.py        # Connection pools and sessions factory
│   ├── alembic/               # Database revisions migration control
│   ├── requirements.txt       # Python libraries definition
│   └── Dockerfile             # FastAPI service container file
└── frontend/
    ├── src/
    │   ├── components/        # React components (AuthPage, etc.)
    │   ├── App.tsx            # Main ChatGPT workspace & Admin analytics
    │   └── index.css          # Tailwind CSS directives & custom fonts
    ├── nginx.conf             # Nginx reverse proxy routing definition
    └── Dockerfile             # Frontend React static compilation & server
```

---

## Features

1. **Document Grounding**: Restrict context search to a single document or query all uploaded materials.
2. **Evaluation Metrics**: Faithfulness, Answer Relevance, Context Precision, Context Recall, and Latency are evaluated concurrently using `asyncio.gather` for minimal overhead.
3. **Admin Analytics Dashboard**: Custom interactive SVG charts (Line & Area) reporting request trends, average latency curves, hallucination percentage, and evaluation log details.
4. **Persistent Volumes**: Named Local Docker mounts preserve vector indices, database records, and upload files.

---

## Quick Start — Local Development

### Prerequisites
- Node.js (v18+)
- Python (3.10+)

### 1. Setup Backend
1. Open a terminal and enter the `backend` folder:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   # macOS/Linux:
   source .venv/bin/activate
   ```
3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   pip install deepeval
   ```
4. Setup environment file `backend/.env` with your API keys:
   ```env
   PORT=8000
   HOST=0.0.0.0
   ENVIRONMENT=development
   DATABASE_URL=sqlite+aiosqlite:///./ragdb.sqlite
   SECRET_KEY=enterprise-rag-secret-key-2024-super-secure-do-not-share
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   EMBEDDING_PROVIDER=openai
   OPENAI_API_KEY=your_openai_key_here
   GEMINI_API_KEY=your_gemini_key_here
   ```
5. Apply database migrations:
   ```bash
   alembic upgrade head
   ```
6. Start the API server:
   ```bash
   uvicorn app.main:app --reload
   ```

### 2. Setup Frontend
1. Open a new terminal and enter the `frontend` folder:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Start the dev server:
   ```bash
   npm run dev
   ```
4. Visit `http://localhost:5173`. Create an account (first registered user automatically gains the **Admin** role, giving access to the **Analytics Dashboard**).

---

## Production Deployment — Docker Compose

To deploy the entire multi-container architecture in production, run the following:

1. Clone or open the project folder in your terminal.
2. Edit `docker-compose.yml` to supply your `OPENAI_API_KEY` or `GEMINI_API_KEY` environmental keys for live generation.
3. Build and launch all services:
   ```bash
   docker-compose up --build -d
   ```
4. Once completed:
   - **Frontend App**: Accessible at [http://localhost](http://localhost) (Port 80)
   - **Backend API**: Reverse proxied to [http://localhost/api](http://localhost/api) (Internal Port 8000)
   - **Database**: PostgreSQL database internally connected on port 5432.

To shutdown the system:
```bash
docker-compose down
```
All documents, user records, and database rows are persisted on your host machine inside local volume drivers (`pgdata`, `uploads_data`, and `chroma_data`).
