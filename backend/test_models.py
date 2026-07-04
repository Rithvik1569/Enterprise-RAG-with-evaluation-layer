import os
from dotenv import load_dotenv

load_dotenv()
try:
    from google import genai
    client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
    models = client.models.list()
    print([m.name for m in models])
except Exception as e:
    print("Error:", e)
    import traceback
    traceback.print_exc()
