import time, os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

system = open(
    "src/generation/answer_service.py",
    encoding="utf-8"
).read()

# Extract the actual _system_prompt body between return """ and """.strip()
start = system.index('return """') + len('return """')
end = system.index('""".strip()', start)
system_prompt = system[start:end].strip()

print("SYSTEM CHARS:", len(system_prompt))

client = Groq(api_key=os.environ["LLM_API_KEY"])

t = time.perf_counter()

stream = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[
        {"role": "system", "content": system_prompt},
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

for chunk in stream:
    if first_chunk is None:
        first_chunk = time.perf_counter() - t
        print("FIRST CHUNK:", round(first_chunk, 3))

    content = chunk.choices[0].delta.content

    if content and first_token is None:
        first_token = time.perf_counter() - t
        print("FIRST TOKEN:", round(first_token, 3))

print("TOTAL:", round(time.perf_counter() - t, 3))
