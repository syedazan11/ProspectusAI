import os
import time
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
You are NED ProspectusAI, an AI assistant for NED niversity undergraduate prospectuses.

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
        # self.model = os.getenv("LLM_MODEL")

        # if not self.api_key:
        #     raise ValueError("LLM_API_KEY is missing in .env")

        # if not self.model:
        #     raise ValueError("LLM_MODEL is missing in .env")

        self.model = os.getenv(
            "INTERPRETER_MODEL",
            os.getenv("LLM_MODEL"),
        )

        if not self.api_key:
            raise ValueError("LLM_API_KEY is missing in .env")

        if not self.model:
            raise ValueError(
                "INTERPRETER_MODEL or LLM_MODEL is missing in .env"
            )

        if self.provider == "groq":
            self.client = Groq(api_key=self.api_key, timeout=50.0, max_retries=0,)

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

    def generate_conversation(
        self,
        messages: list[dict[str, str]],
    ) -> str:
        """
        Generates a conversational response using the
        supplied in-memory conversation history.

        This is separate from generate_answer() because
        conversational requests must not use the
        prospectus-only system prompt.
        """

        conversation_system_prompt = """
You are the conversational component of ProspectusAI.

The user's request has already been classified as a
conversation request.

Use the conversation history to understand the user's
current message and respond naturally.

Rules:

1. Use the conversation history as your memory.
2. You may recall information the user previously told you.
3. Do not invent personal information or facts.
4. If the requested information is not present in the
   conversation history, say that you do not know.
5. Keep responses natural, concise, and helpful.
6. Do not answer university prospectus questions.
7. Do not perform prospectus retrieval.
"""

        if self.provider in ("groq", "openai"):

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": conversation_system_prompt,
                    },
                    *messages,
                ],
                temperature=0.2,
                max_tokens=512,
            )

            return (
                response.choices[0].message.content
                or ""
            )

        elif self.provider == "anthropic":

            if not messages:
                return ""

            response = self.client.messages.create(
                model=self.model,
                system=conversation_system_prompt,
                messages=messages,
                max_tokens=512,
                temperature=0.2,
            )

            return response.content[0].text

        raise RuntimeError(
            f"Unsupported LLM provider: {self.provider}"
        )
        
    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 400,
        reasoning_effort: str | None = None,
        response_format: dict | None = None,
    ) -> str:
        """
        Runs a structured extraction task.

        Used by graph extraction and other pipelines
        that need raw JSON-like LLM output.
        """

        if self.provider in ("groq", "openai"):

            llm_start = time.perf_counter()

            # response = self.client.chat.completions.create(
            #     model=self.model,
            #     messages=[
            #         {
            #             "role": "system",
            #             "content": system_prompt,
            #         },
            #         {
            #             "role": "user",
            #             "content": user_prompt,
            #         },
            #     ],
            #     temperature=0,
            #     max_tokens=max_tokens,
            # )
            kwargs = dict(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                temperature=0,
                max_tokens=max_tokens,
            )

            if reasoning_effort is not None:
                kwargs["reasoning_effort"] = reasoning_effort

            if response_format is not None:
                kwargs["response_format"] = response_format

            # api_start = time.perf_counter()

            # # response = self.client.chat.completions.create(
            # #     **kwargs
            # # )
            # try:
            #     response = self.client.chat.completions.create(
            #         **kwargs
            #     )
            # # except Exception as exc:
            # #     from groq import RateLimitError

            # #     if isinstance(exc, RateLimitError):
            # #         print(f"[INTERPRETER RATE LIMIT] {exc}")
            # #         raise RuntimeError(
            # #             "ProspectusAI is temporarily busy due to the AI provider's "
            # #             "rate limit. Please wait a few seconds and try again."
            # #         ) from exc

            # #     raise
            # except Exception as exc:
            #     from groq import RateLimitError
            #     import re

            #     if isinstance(exc, RateLimitError):
            #         error_text = str(exc)
            #         print(f"[INTERPRETER RATE LIMIT] {error_text}")

            #         wait_match = re.search(
            #             r"try again in\s+([\d.]+)\s*(ms|seconds?|s|minutes?|m)",
            #             error_text,
            #             re.IGNORECASE,
            #         )

            #         wait_seconds = None

            #         if wait_match:
            #             amount = float(wait_match.group(1))
            #             unit = wait_match.group(2).lower()

            #             if unit.startswith("m"):
            #                 wait_seconds = amount * 60
            #             elif unit == "ms":
            #                 wait_seconds = amount / 1000
            #             else:
            #                 wait_seconds = amount

            #         if "tokens per day" in error_text.lower():
            #             raise RuntimeError(
            #                 "ProspectusAI's daily AI token quota has been exhausted. "
            #                 + (
            #                     f"Please try again in about {int(wait_seconds)} seconds."
            #                     if wait_seconds is not None
            #                     else "Please try again later."
            #                 )
            #             ) from exc

            #         if wait_seconds is not None and wait_seconds > 30:
            #             raise RuntimeError(
            #                 f"ProspectusAI is temporarily rate-limited. "
            #                 f"Please try again in about {int(wait_seconds)} seconds."
            #             ) from exc

            #     raise
            api_start = time.perf_counter()
            max_attempts = 4  # Initial request + 2 retries
            response = None

            for attempt in range(max_attempts):
                try:
                    response = self.client.chat.completions.create(**kwargs)
                    break

                except Exception as exc:
                    from groq import RateLimitError
                    import re

                    if not isinstance(exc, RateLimitError):
                        raise

                    error_text = str(exc)
                    print(f"[INTERPRETER RATE LIMIT] {error_text}")

                    wait_match = re.search(
                        r"try again in\s+([\d.]+)\s*(ms|seconds?|s|minutes?|m)",
                        error_text,
                        re.IGNORECASE,
                    )

                    wait_seconds = None

                    if wait_match:
                        amount = float(wait_match.group(1))
                        unit = wait_match.group(2).lower()
            
                        if unit == "ms":
                            wait_seconds = amount / 1000
                        elif unit.startswith("m"):
                            wait_seconds = amount * 60
                        else:
                            wait_seconds = amount

                    if "tokens per day" in error_text.lower():
                        raise RuntimeError(
                            "ProspectusAI's daily AI token quota has been exhausted. "
                            + (
                                f"Please try again in about {int(wait_seconds)} seconds."
                                if wait_seconds is not None
                                else "Please try again later."
                            )
                        ) from exc

                    if wait_seconds is None or wait_seconds > 30:
                        raise RuntimeError(
                            "ProspectusAI is temporarily rate-limited. "
                            + (
                                f"Please try again in about {int(wait_seconds)} seconds."
                                if wait_seconds is not None
                                else "Please try again later."
                            )
                        ) from exc

                    if attempt == max_attempts - 1:
                        raise RuntimeError(
                            "ProspectusAI is still rate-limited after retrying. "
                            "Please try again shortly."
                        ) from exc

                    print(
                        f"[INTERPRETER RETRY] Attempt {attempt + 2}/{max_attempts}; "
                        f"waiting {wait_seconds:.2f}s"
                    )
                    time.sleep(wait_seconds)

            if response is None:
                raise RuntimeError("ProspectusAI could not obtain an AI response.")

            print(
            f"[INTERPRETER API WAIT] "
            f"{time.perf_counter() - api_start:.3f}s"
            )
            print("[INTERPRETER RESPONSE RECEIVED]")

            llm_time = time.perf_counter() - llm_start

            usage = getattr(response, "usage", None)
            print("[INTERPRETER RAW USAGE]", usage)

            print(
                f"[INTERPRETER LLM TIMING] request: "
                f"{llm_time:.3f}s"
            )
            if usage is not None:
                print(
                    "[INTERPRETER LLM USAGE] "
                    f"prompt={getattr(usage, 'prompt_tokens', None)}, "
                    f"completion={getattr(usage, 'completion_tokens', None)}, "
                    f"total={getattr(usage, 'total_tokens', None)}"
                )

                completion_details = getattr(
                    usage,
                    "completion_tokens_details",
                    None,
                )

                if completion_details is not None:
                    print(
                        "[INTERPRETER LLM DETAILS] "
                        f"reasoning={getattr(completion_details, 'reasoning_tokens', None)}"
                    )

            print(
                "\n========== GROQ STRUCTURED RESPONSE =========="
            )
            print("MODEL:", response.model)
            print(
                "FINISH:",
                response.choices[0].finish_reason,
            )
            print(
                "MESSAGE:",
                response.choices[0].message,
            )
            print(
                "CONTENT:",
                repr(
                    response.choices[0].message.content
                ),
            )
            print(
                "==============================================="
            )

            return (
                response.choices[0].message.content
                or ""
            )

        if self.provider == "anthropic":

            response = self.client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt,
                    }
                ],
                max_tokens=4096,
                temperature=0,
            )

            return response.content[0].text

        raise RuntimeError(
            f"Unsupported LLM provider: {self.provider}"
        )