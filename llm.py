import os
from google import genai

# Create client using environment variable
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def get_llm_decision(prompt: str):
    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=prompt
        )

        return response.text

    except Exception as e:
        return f"LLM Error: {str(e)}"
