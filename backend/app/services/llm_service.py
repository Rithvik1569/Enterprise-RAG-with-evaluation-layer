import logging
import httpx
from app.config import settings
from app.schemas.document import RetrievalChunk

logger = logging.getLogger("rag_pipeline")


class LLMService:
    """Service to interact with LLM providers (Gemini, OpenAI, or Fallback Mock)."""

    def __init__(self):
        self.gemini_key = settings.GEMINI_API_KEY
        self.openai_key = settings.OPENAI_API_KEY
        self.groq_key = getattr(settings, "GROQ_API_KEY", None)

    def build_prompt(self, query: str, chunks: list[RetrievalChunk]) -> str:
        """Constructs a context-aware prompt using the retrieved document chunks."""
        if not chunks:
            return f"User Question: {query}\n\nNo document context was found in the database. Please answer to the best of your knowledge but specify that no relevant documents were found."

        context_str = ""
        for i, chunk in enumerate(chunks, 1):
            context_str += f"--- Source {i}: {chunk.filename} (Chunk {chunk.chunk_index}) ---\n"
            context_str += f"{chunk.text}\n\n"

        prompt = (
            "You are a helpful and precise RAG assistant. First, try to answer the user's question using the provided document context below.\n"
            "If the context contains the answer, refer to the sources where appropriate (e.g., [Source 1], [Source 2]).\n"
            "If the context does not contain the answer, answer to the best of your knowledge like ChatGPT, but clearly state that your answer is based on general knowledge and not found in the provided documents.\n\n"
            f"=== DOCUMENT CONTEXT ===\n{context_str}========================\n\n"
            f"User Question: {query}\n\n"
            "Answer:"
        )
        return prompt

    async def generate_answer(self, query: str, chunks: list[RetrievalChunk]) -> str:
        """Generates an answer from the best available LLM provider or fallback mock."""
        prompt = self.build_prompt(query, chunks)
        last_error = None

        # 0. Try Groq (Preferred)
        if self.groq_key:
            try:
                logger.info("Generating response using Groq API (llama-3.1-8b-instant)...")
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=self.groq_key, base_url="https://api.groq.com/openai/v1")
                response = await client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": "You are a helpful RAG assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    max_tokens=800
                )
                return response.choices[0].message.content
            except Exception as e:
                last_error = f"Groq API Error: {str(e)}"
                logger.error("Failed to generate response with Groq API: %s. Falling back...", str(e))

        # 1. Try Gemini
        if self.gemini_key:
            try:
                logger.info("Generating response using Gemini API...")
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_key}"
                headers = {"Content-Type": "application/json"}
                payload = {
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }]
                }
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    answer = data["candidates"][0]["content"]["parts"][0]["text"]
                    return answer
            except Exception as e:
                last_error = f"Gemini API Error: {str(e)}"
                logger.error("Failed to generate response with Gemini API: %s. Falling back...", str(e))

        # 2. Try OpenAI
        if self.openai_key:
            try:
                logger.info("Generating response using OpenAI API...")
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=self.openai_key)
                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a helpful RAG assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    max_tokens=800
                )
                return response.choices[0].message.content
            except Exception as e:
                last_error = f"OpenAI API Error: {str(e)}"
                logger.error("Failed to generate response with OpenAI API: %s. Falling back...", str(e))

        # 3. Fallback Mock response
        logger.warning("No functional LLM API key available or calls failed. Using fallback mock responder.")
        return self._generate_mock_response(query, chunks, error_msg=last_error)

    async def generate_text(self, prompt: str) -> str:
        """Generates content from the best available LLM provider for any arbitrary prompt."""
        # 0. Try Groq (Preferred)
        if self.groq_key:
            try:
                logger.info("Generating text using Groq API...")
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=self.groq_key, base_url="https://api.groq.com/openai/v1")
                response = await client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.0,
                    max_tokens=1000
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error("Failed to generate text with Groq API: %s. Falling back...", str(e))

        # 1. Try Gemini
        if self.gemini_key:
            try:
                logger.info("Generating text using Gemini API...")
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_key}"
                headers = {"Content-Type": "application/json"}
                payload = {
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }]
                }
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                logger.error("Failed to generate text with Gemini API: %s. Falling back...", str(e))

        # 2. Try OpenAI
        if self.openai_key:
            try:
                logger.info("Generating text using OpenAI API...")
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=self.openai_key)
                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.0,
                    max_tokens=1000
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error("Failed to generate text with OpenAI API: %s. Falling back...", str(e))

        # 3. Fallback Mock response
        logger.warning("No functional LLM API key available or calls failed. Using fallback mock responder.")
        return "mock_eval_response"

    def _generate_mock_response(self, query: str, chunks: list[RetrievalChunk], error_msg: str = None) -> str:
        """Generates a mock response simulating LLM behavior based on retrieved chunks."""
        if not chunks:
            return (
                "👋 Hello! I am running in development fallback mode. I searched the database but found no relevant document chunks. "
                "Please upload a document to the Knowledge Base first so I can find matching information to answer your question!"
            )

        citations_list = [f"**{c.filename}** (Chunk {c.chunk_index}, relevance score: {c.score:.4f})" for c in chunks]
        
        # Simple extraction of key sentences/lines containing user query words to synthesize a mock response
        matched_sentences = []
        query_words = [w.lower() for w in query.split() if len(w) > 3]
        
        for c in chunks:
            for line in c.text.split('.'):
                line = line.strip()
                if not line:
                    continue
                # If query word matches line, capture it
                if any(qw in line.lower() for qw in query_words):
                    matched_sentences.append(line)
                    if len(matched_sentences) >= 3:
                        break
            if len(matched_sentences) >= 3:
                break

        if not matched_sentences:
            # Grab first few sentences of first chunk as a summary
            first_chunk_text = chunks[0].text.replace('\n', ' ')
            matched_sentences = first_chunk_text.split('.')[:2]

        summary = ". ".join([s.strip() for s in matched_sentences if s.strip()]) + "."
        
        error_note = f"\n\n*API Error Details:* `{error_msg}`" if error_msg else ""
        
        answer = (
            "⚙️ **[Development Fallback Mode]**\n\n"
            f"Based on the retrieved document context, here is what I found:\n\n"
            f"> \"...{summary}...\"\n\n"
            "This information was retrieved from the following sources:\n" + 
            "\n".join([f"- [Source {i+1}] {cite}" for i, cite in enumerate(citations_list)]) + "\n\n"
            "*Note: The LLM API is currently unavailable, so I cannot provide a ChatGPT-like general answer.*" + error_note + "\n"
            "*Please check your `.env` API keys and Quota limits!*"
        )
        return answer
