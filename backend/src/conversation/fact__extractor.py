from __future__ import annotations

import re

from src.conversation.session import ConversationSession


class UserFactExtractor:
    """
    Deterministic, regex-based extraction and recall of simple
    conversational user facts (name, semester, hometown, interests)
    for the lifetime of a single chat.

    This is intentionally NOT LLM-based: fact storage and fact
    recall must be served straight from the in-memory
    ConversationSession so answers like "What's my name?" never
    depend on retrieval or generation.
    """

    # --- statement ("I am telling you something") patterns -----------
    #
    # Order matters. More specific patterns (semester / city / likes)
    # are tried before the generic name patterns so that a message
    # like "I'm in fourth semester" or "I'm from Karachi" is captured
    # correctly instead of being swallowed by a name pattern.

    _SEMESTER_PATTERNS = (
        re.compile(
            r"\b(?:i'?m|i am)\s+in\s+(?:the\s+)?([a-zA-Z0-9]+)\s+semester\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bsemester\s+(?:is\s+|number\s+)?"
            r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten|"
            r"first|second|third|fourth|fifth|sixth|seventh|eighth|"
            r"ninth|tenth)\b",
            re.IGNORECASE,
        ),
    )

    _CITY_PATTERNS = (
        re.compile(
            r"\b(?:i'?m|i am)\s+from\s+([A-Za-z][A-Za-z ]*)",
            re.IGNORECASE,
        ),
    )

    _LIKES_PATTERNS = (
        re.compile(
            r"\bi\s+like\s+([A-Za-z0-9][A-Za-z0-9 ]*)",
            re.IGNORECASE,
        ),
    )

    _NAME_PATTERNS = (
        re.compile(
            r"\bmy name is\s+([A-Za-z][A-Za-z ]*)",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bcall me\s+([A-Za-z][A-Za-z ]*)",
            re.IGNORECASE,
        ),
    )

    # --- recall ("ask me back what I told you") patterns --------------

    _RECALL_PATTERNS: dict[str, tuple[re.Pattern, ...]] = {
        "name": (
            re.compile(r"\bwhat'?s my name\b", re.IGNORECASE),
            re.compile(r"\bwhat is my name\b", re.IGNORECASE),
            re.compile(r"\bdo you (?:know|remember) my name\b", re.IGNORECASE),
        ),
        "semester": (
            re.compile(r"\bwhich semester\b", re.IGNORECASE),
            re.compile(r"\bwhat semester\b", re.IGNORECASE),
        ),
        "city": (
            re.compile(r"\bwhere am i from\b", re.IGNORECASE),
            re.compile(r"\bwhich city am i from\b", re.IGNORECASE),
        ),
        "likes": (
            re.compile(r"\bwhat do i like\b", re.IGNORECASE),
            re.compile(r"\bwhat did i (?:say i )?like\b", re.IGNORECASE),
        ),
    }

    _FACT_LABELS: dict[str, str] = {
        "name": "your name is",
        "semester": "you're in",
        "city": "you're from",
        "likes": "you like",
    }

    @classmethod
    def remember(
        cls,
        query: str,
        session: ConversationSession,
    ) -> list[str]:
        """
        Look for factual statements in `query` and store them on the
        session's UserFacts. Returns the fact keys that were stored.
        """

        stored: list[str] = []

        for key, patterns in (
            ("semester", cls._SEMESTER_PATTERNS),
            ("city", cls._CITY_PATTERNS),
            ("likes", cls._LIKES_PATTERNS),
        ):
            value = cls._first_match(patterns, query)

            if value:
                session.user_facts.remember(key, value)
                stored.append(key)

        # Only look for a name if nothing more specific already
        # matched in this message, otherwise "I'm from Karachi"
        # would also get misread as a name.
        if not stored:

            value = cls._first_match(cls._NAME_PATTERNS, query)

            if value:
                session.user_facts.remember("name", value)
                stored.append("name")

        return stored

    @classmethod
    def recall(
        cls,
        query: str,
        session: ConversationSession,
    ) -> str | None:
        """
        If `query` is asking for a previously remembered fact,
        return an answer built entirely from the session. Returns
        None when the query doesn't look like a recall question, so
        the caller can fall through to other handling.
        """

        for key, patterns in cls._RECALL_PATTERNS.items():

            if not any(pattern.search(query) for pattern in patterns):
                continue

            value = session.user_facts.get(key)

            if value is None:
                return (
                    "I don't have that saved for this chat yet. "
                    "Tell me and I'll remember it for the rest of "
                    "our conversation."
                )

            label = cls._FACT_LABELS.get(key, key)

            return f"You told me {label} {value}."

        return None

    @classmethod
    def label_for(cls, key: str) -> str:

        return cls._FACT_LABELS.get(key, key)

    @staticmethod
    def _first_match(
        patterns: tuple[re.Pattern, ...],
        query: str,
    ) -> str | None:

        for pattern in patterns:

            match = pattern.search(query)

            if match:
                return match.group(1).strip()

        return None