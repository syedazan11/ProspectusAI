import os

from dotenv import load_dotenv
from groq import Groq
from openai import OpenAI
from anthropic import Anthropic

load_dotenv()

class LLMService:
    """
    Handles interactions with the LLM.
    """

    SYSTEM_PROMPT = """
You are ProspectusAI, an AI assistant for university undergraduate prospectuses.

Your job is to answer ONLY questions related to the provided undergraduate prospectus.

Rules:

1. Use ONLY the provided context.
2. Never make up facts.
3. If the answer is not available in the provided context, respond:
   "I couldn't find this information in the provided prospectus."
4. Mention the page number whenever the information comes from a retrieved chunk.
5. If multiple pages contain relevant information, combine them into one complete answer.
6. Answer clearly and professionally.
7. Ignore questions unrelated to the undergraduate prospectus.
"""

    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "groq").lower()
        self.api_key = os.getenv("LLM_API_KEY")
        self.model = os.getenv("LLM_MODEL")

        if not self.api_key:
            raise ValueError("LLM_API_KEY is missing in .env")

        if not self.model:
            raise ValueError("LLM_MODEL is missing in .env")

        if self.provider == "groq":
            self.client = Groq(api_key=self.api_key)

        elif self.provider == "openai":
            self.client = OpenAI(api_key=self.api_key)

        elif self.provider == "anthropic":
            self.client = Anthropic(api_key=self.api_key)

        else:
            raise ValueError(
                f"Unsupported LLM provider: {self.provider}"
            )

    def generate_answer(
        self,
        question: str,
        context: str,
    ) -> str:

        user_message = f"""Use the following retrieved prospectus context to answer the question.

        CONTEXT:
        {context}

        QUESTION:
        {question}
        """

        if self.provider in ("groq", "openai"):

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self.SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": user_message,
                    },
                ],
                temperature=0.1,
            )

            return response.choices[0].message.content or ""

        elif self.provider == "anthropic":

            response = self.client.messages.create(
                model=self.model,
                system=self.SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": user_message,
                    }
                ],
                max_tokens=1024,
                temperature=0.1,
            )

            return response.content[0].text