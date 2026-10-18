import time
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.environ["LLM_API_KEY"])

context = """
PASTE THE SAME CONTEXT YOU USED IN THE PREVIOUS TEST HERE
"""

table_instruction = ""

user_prompt = f"""
{table_instruction}

Use the supplied prospectus context as the complete evidence set.
Answer the user's question directly.

- If the answer is supported anywhere in the context, provide the complete
  supported answer.
- Combine relevant sections when needed, while preserving distinctions.
- If only part is supported, provide that supported part.
- If the answer is genuinely absent from the entire context, follow the
  fallback rule in the system instructions.
- Do not mention page numbers.

PROSPECTUS CONTEXT:
{context}

USER QUESTION:
What are the eligibility criteria for admission?
""".strip()

print("USER PROMPT CHARS:", len(user_prompt))

t = time.perf_counter()

stream = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[
        {
            "role": "system",
            "content": "You are a helpful assistant."
        },
        {
            "role": "user",
            "content": user_prompt
        },
    ],
    temperature=0.0,
    max_tokens=1200,
    stream=True,
)

print("CREATE:", round(time.perf_counter() - t, 3))

first_chunk = None
first_token = None

for chunk in stream:
    if first_chunk is None:
        first_chunk = time.perf_counter() - t
        print("FIRST CHUNK:", round(first_chunk, 3))

    content = chunk.choices[0].delta.content

    if content and first_token is None:
        first_token = time.perf_counter() - t
        print("FIRST TOKEN:", round(first_token, 3))

print("TOTAL:", round(time.perf_counter() - t, 3))