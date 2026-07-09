# Enterprise RAG SaaS System

Enterprise RAG is a production-ready, enterprise-grade Retrieval-Augmented Generation (RAG) SaaS platform. It combines real-time document grounding search with an automated strict evaluation layer (faithfulness, relevance, precision, recall) and a modern admin analytics suite.

---

## Technical Stack & Architecture

- **Frontend**: React (v19) + JavaScript + Vite + Tailwind CSS (v4)
- **Backend**: FastAPI + Python (3.10+)
- **Database**: MongoDB (Production & Development)
- **Vector Database**: ChromaDB (for high-dimensional vector embeddings)
- **Evaluation Engine**: Parallel prompt evaluations modeled after DeepEval & Ragas definitions, powered by Groq (Llama 3.1) and Google Gemini for strict zero-hallucination tracking.
- **LLM / Embedding**: Google Gemini (`models/gemini-embedding-001` or similar), optionally OpenAI.
- **Deployment**: Vercel (Frontend) and Render (Backend API)

---

## Features

1. **Document Grounding**: Restrict context search to a single document or query all uploaded materials seamlessly.
2. **Strict Evaluation Metrics (Zero-Hallucination)**: Faithfulness, Answer Relevance, Context Precision, and Context Recall are evaluated concurrently using `asyncio.gather`. The evaluation prompt enforces absolute strictness, punishing completely irrelevant context or hallucinated answers with 0% exact values, and displays integer-perfect metrics in the UI.
3. **Structured Formatted Chat**: The UI flawlessly renders complex Markdown spacing, ordered lists, and neatly formatted paragraphs utilizing `whitespace-pre-wrap` styling.
4. **Admin Analytics Dashboard**: Custom interactive SVG charts reporting request trends, average latency curves, hallucination percentages (where Faithfulness < 80%), and evaluation log details.
5. **Persistent Storage**: Robust storage of vectors in ChromaDB and user records/history in MongoDB.

---

## Directory Structure

```text
Final AI project/
├── docker-compose.yml          # Full-stack orchestrator (if deploying via Docker)
├── backend/
│   ├── app/
│   │   ├── models/            # Database schemas & Document mappings
│   │   ├── routes/            # FastAPI routes (chat, admin, etc.)
│   │   ├── evaluation/        # Ragas_eval.py for strict precision/recall metrics
│   │   └── main.py            # API Server lifespan and routers registration
│   ├── .env                   # Environment variables (MongoDB, Groq, Gemini keys)
│   └── requirements.txt       # Python libraries definition
└── frontend/
    ├── src/
    │   ├── components/        # React components (Admin Dashboard, Chat)
    │   ├── App.jsx            # Main ChatGPT workspace, Analytics & Metrics formatting
    │   └── index.css          # Tailwind CSS directives (with formatting fixes)
    ├── .env.example           # Frontend environment example
    └── package.json           # React static compilation & server dependencies
```

---

## Quick Start — Local Development

### Prerequisites
- Node.js (v18+)
- Python (3.10+)
- MongoDB connection URI (e.g., MongoDB Atlas)

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
   ```
4. Setup environment file `backend/.env` with your API keys and MongoDB URL:
   ```env
   PORT=8000
   HOST=0.0.0.0
   ENVIRONMENT=development
   MONGODB_URL="mongodb+srv://<user>:<password>@cluster0.../ragdb"
   DATABASE_NAME="ragdb"
   SECRET_KEY="your-secure-secret-key"
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   EMBEDDING_PROVIDER=gemini
   GEMINI_API_KEY="your_gemini_key_here"
   GROQ_API_KEY="your_groq_key_here"
   ```
5. Start the API server:
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
4. Visit `http://localhost:5173`. The first registered user automatically gains the **Admin** role, giving access to the **Analytics Dashboard**.

---

## Production Deployment

This project is configured to be easily deployed using modern cloud platforms:

### 1. Backend Deployment (Render)
1. Push your repository to GitHub.
2. Go to [Render.com](https://render.com) and create a new **Web Service**.
3. Connect your GitHub repository and select the `backend` folder as the Root Directory.
4. Set the Build Command to `pip install -r requirements.txt`.
5. Set the Start Command to `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
6. Add all the environment variables from your `.env` file (e.g., `MONGODB_URL`, `GEMINI_API_KEY`, `GROQ_API_KEY`, etc.) in the Render dashboard.

### 2. Frontend Deployment (Vercel)
1. Go to [Vercel.com](https://vercel.com) and create a new **Project**.
2. Import your GitHub repository.
3. Set the Framework Preset to **Vite**.
4. Set the Root Directory to `frontend`.
5. Add any required frontend environment variables (like your newly deployed Render Backend API URL, e.g. `VITE_API_URL=https://your-backend.onrender.com`).
6. Click **Deploy**.

Your application will now be fully live, with the frontend hosted on Vercel and the backend reliably running on Render.
