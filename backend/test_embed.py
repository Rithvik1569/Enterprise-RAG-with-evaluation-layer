import asyncio
from app.config import settings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

def test_embed():
    print(f"Testing Gemini Embedding with model: {settings.EMBEDDING_MODEL}")
    embeddings = GoogleGenerativeAIEmbeddings(
        google_api_key=settings.GEMINI_API_KEY,
        model="models/gemini-embedding-2" # Try gemini-embedding-2
    )
    res = embeddings.embed_query("Hello world")
    print(f"Success! Vector length: {len(res)}")

if __name__ == "__main__":
    test_embed()
