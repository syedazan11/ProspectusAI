import time, os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.environ["LLM_API_KEY"])

t = time.perf_counter()

stream = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[
        {
            "role": "system",
            "content": "You are a helpful assistant. Answer using the supplied prospectus context."
        },
        {
            "role": "user",
            "content": "What are the eligibility criteria for Mechanical Engineering?"
        }
    ],
    temperature=0.0,
    max_tokens=1200,
    stream=True,
)

print("CREATE:", round(time.perf_counter() - t, 3))

first_chunk = None
first_token = None
text = ""

for chunk in stream:
    if first_chunk is None:
        first_chunk = time.perf_counter() - t
        print("FIRST CHUNK:", round(first_chunk, 3))

    content = chunk.choices[0].delta.content

    if content:
        if first_token is None:
            first_token = time.perf_counter() - t
            print("FIRST TOKEN:", round(first_token, 3))
        text += content

print("TOTAL:", round(time.perf_counter() - t, 3))
print("TEXT:", text[:300])
