from __future__ import annotations

import re

from src.conversation.models import (
    RequestType,
)


class Classifier:

    GREETING = re.compile(
        r"\b("
        r"hi|hello|hey|heya|hiya|"
        r"good morning|good afternoon|good evening|"
        r"assalam|assalamualaikum|assalamu alaikum|"
        r"salam|aoa|asalam"
        r")\b",
        re.IGNORECASE,
    )

    GOODBYE = re.compile(
        r"\b("
        r"bye|goodbye|see you|see ya|"
        r"take care|allah hafiz|khuda hafiz|"
        r"farewell|later|good night"
        r")\b",
        re.IGNORECASE,
    )

    SYSTEM = re.compile(
        r"\b("
        r"who are you|"
        r"what are you|"
        r"introduce yourself|"
        r"what can you do|"
        r"help|"
        r"how do you work|"
        r"how does this work|"
        r"what is this system|"
        r"what is prospectusai|"
        r"are you chatgpt|"
        r"are you ai|"
        r"your purpose|"
        r"your capabilities|"
        r"what can i ask|"
        r"commands|"
        r"features"
        r")\b",
        re.IGNORECASE,
    )

    # CONVERSATION = re.compile(
    #     r"\b("
    #     r"my name is|"
    #     r"i am|i'm|"
    #     r"i like|i love|i enjoy|"
    #     r"i don't like|i dislike|"
    #     r"what is my name|"
    #     r"what did i tell you|"
    #     r"do you remember|"
    #     r"remember that|"
    #     r"i prefer|"
    #     r"my favorite|"
    #     r")\b",
    #     re.IGNORECASE,
    # )
    PERSONAL = re.compile(
        r"^\s*(?:"
        r"i like|"
        r"i love|"
        r"i enjoy|"
        r"i prefer|"
        r"my name is|"
        r"my favorite|"
        r"i don't like|"
        r"i dislike"
        r")\b",
        re.IGNORECASE,
    )

    IRRELEVANT = re.compile(
        r"\b("
        r"weather|temperature|forecast|rain|"
        r"instagram|facebook|youtube|tiktok|twitter|x|snapchat|linkedin|reddit|"
        r"football|soccer|cricket|basketball|tennis|formula 1|f1|"
        r"ipl|world cup|champions league|"
        r"movie|movies|film|netflix|anime|manga|"
        r"music|song|songs|album|spotify|"
        r"capital of|president of|prime minister|"
        r"population of|currency of|"
        r"bitcoin|ethereum|crypto|stock market|share market|"
        r"recipe|cook|cooking|food recipe|"
        r"news|latest news"
        r")\b",
        re.IGNORECASE,
    )

    @classmethod
    def classify(
        cls,
        query: str,
    ) -> RequestType:

        query = query.strip()

        if cls.GREETING.search(query):
            return RequestType.GREETING

        if cls.GOODBYE.search(query):
            return RequestType.GOODBYE

        if cls.SYSTEM.search(query):
            return RequestType.SYSTEM

        # if cls.CONVERSATION.search(query):
        #     return RequestType.CONVERSATION

        if cls.PERSONAL.search(query):
            return RequestType.CONVERSATION


        if cls.IRRELEVANT.search(query):
            return RequestType.IRRELEVANT

        return RequestType.UNKNOWN