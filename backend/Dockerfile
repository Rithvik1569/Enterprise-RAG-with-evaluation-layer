FROM python:3.11-slim

WORKDIR /workspace/backend

# Install system dependencies needed for compiling python libraries if any
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install deepeval for the evaluation layers
RUN pip install --no-cache-dir deepeval

# Copy backend source
COPY . .

EXPOSE 8000

# Execute migrations and start FastAPI server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
