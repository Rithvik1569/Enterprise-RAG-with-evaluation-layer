import os
from dotenv import load_dotenv
import asyncio
from openai import AsyncOpenAI
import sys

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

async def test():
    if not api_key:
        print("No OPENAI_API_KEY found in .env")
        return
    print(f"Testing key: {api_key[:10]}...")
    client = AsyncOpenAI(api_key=api_key)
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "hello"}],
            max_tokens=5
        )
        print("Success! Key works.")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test())
