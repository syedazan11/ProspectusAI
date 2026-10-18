from __future__ import annotations
 
import re
 
from src.retrieval.models import (
    RetrievalIntent,
    RetrievalPlan,
)
 
 
class RetrievalPlanner:
 
    PEOPLE_KEYWORDS = {
        "faculty",
        "staff",
        "teacher",
        "teachers",
        "professor",
        "chairperson",
        "co-chairperson",
        "co chairperson",
        "Co-Chairperson",
        "chairman",
        "principal",
        "dean",
        "vice chancellor",
        "pro vice chancellor",
        "Pro Vice-Chancellor",
        "pro vice-chancellor",
        "vice-chancellor",
        "registrar",
        "controller",
        "lecturer",
        "associate professor",
        "assistant professor",
        "director",
        "it manager",
        "it managers",
    }
 
    FEE_KEYWORDS = {
        "fee",
        "fees",
        "tuition",
        "payment",
        "deposit",
        "challan",
        "security deposit",
        "security",
        "payable",
        "amount",
        "cost",
        "charges",
        "self finance fee",
    }
 
    ADMISSION_CODE = re.compile(
        r"\b(?:R|SF)[-\s]?\d+(?:\s*\([A-Z]\)|[A-Z])?(?![A-Za-z0-9])",
        re.IGNORECASE,
    )
 
    WORD = re.compile(r"[a-zA-Z0-9()/-]+")

    STOP_WORDS = {
    "who",
    "what",
    "when",
    "where",
    "which",
    "whom",
    "whose",
    "is",
    "are",
    "was",
    "were",
    "be",
    "am",
    "do",
    "does",
    "did",
    "the",
    "a",
    "an",
    "of",
    "for",
    "to",
    "in",
    "on",
    "at",
    "and",
    "or",
    "with",
    "by",
    "from",
    "about",
    "as",
    "that",
    "this",
    "these",
    "those",
    "available",
    }

    TOPIC_KEYWORDS = {
    "facilities",
    "facility",
    "labs",
    "laboratories",
    "laboratory",
    "fees",
    "fee",
    "workshops",
    "workshop",
    "seminars",
    "research facilities",
    "equipment",
    "eligibility",
    "admission",
    "requirements",
    "criteria",
    "scholarships",
    "scholarship",
    "hostel",
    "hostels",
    "accommodation",
    "faculty",
    "staff",
    "department",
    "programs",
    "program",
    "contact",
    "phone",
    "email",
    "location",
    "campus",
    "deadline",
    "deadlines",
    "dates",
    "date",
    "duration",
    "objectives",
    "objective",
    "research",
    "researches",
   }
 
    PHRASE = re.compile(r'"([^"]+)"')
 
    CODE_PARTS = re.compile(
        r"^(?P<prefix>R|SF)[-\s]?(?P<digits>\d+)"
        r"(?:\s*\((?P<paren_letter>[A-Za-z])\)|(?P<bare_letter>[A-Za-z]))?$",
        re.IGNORECASE,
    )
 
    # Keyword sets matched as whole words/phrases with boundaries, longest
    # phrases first so multi-word keywords take precedence over substrings.
    # _PEOPLE_PATTERN = re.compile(
    #     r"\b(?:"
    #     + "|".join(re.escape(k) for k in sorted(PEOPLE_KEYWORDS, key=len, reverse=True))
    #     + r")\b",
    #     re.IGNORECASE,
    # )

    _PEOPLE_PATTERN = re.compile(
        r"\b(?:"
        + "|".join(
            re.escape(k) + r"s?"
            for k in sorted(PEOPLE_KEYWORDS, key=len, reverse=True)
        )
        + r")\b",
        re.IGNORECASE,
    )
 
    _FEE_PATTERN = re.compile(
        r"\b(?:"
        + "|".join(re.escape(k) for k in sorted(FEE_KEYWORDS, key=len, reverse=True))
        + r")\b",
        re.IGNORECASE,
    )
 
    @classmethod
    def plan(
        cls,
        query: str,
        *,
        is_follow_up: bool = False,
    ) -> RetrievalPlan:
        cleaned = query.strip()
 
        intent = cls._detect_intent(cleaned)
        codes = cls._extract_codes(cleaned)
        keywords = cls._extract_keywords(cleaned)
        phrases = cls._extract_phrases(cleaned)

        topics = cls._extract_topics(
            keywords,
            phrases,
        )

        entities = cls._extract_entities(
            keywords,
            phrases,
            topics,
        )
 
        return RetrievalPlan(
            raw_query=cleaned,
            intent=intent,
            admission_codes=codes,
            keywords=keywords,
            phrases=phrases,
            entities=entities,
            topics=topics,
            is_follow_up=is_follow_up,
        )
 
    @classmethod
    def _detect_intent(cls, query: str) -> RetrievalIntent:
        if cls.ADMISSION_CODE.search(query):
            return RetrievalIntent.ADMISSION_CATEGORY
 
        if cls._FEE_PATTERN.search(query):
            return RetrievalIntent.FEES
 
        if cls._PEOPLE_PATTERN.search(query):
            return RetrievalIntent.PEOPLE
 
        return RetrievalIntent.GENERAL
 
 
    @classmethod
    def _extract_codes(cls, query: str) -> list[str]:
        codes: list[str] = []
        seen: set[str] = set()
 
        for match in cls.ADMISSION_CODE.finditer(query):
            normalized = cls._normalize_code(match.group(0))
            if normalized not in seen:
                seen.add(normalized)
                codes.append(normalized)
 
        return codes
 
    @classmethod
    def _normalize_code(cls, code: str) -> str:
        match = cls.CODE_PARTS.match(code.strip())
        if not match:
            return code.strip().upper()
 
        prefix = match.group("prefix").upper()
        digits = match.group("digits")
        letter = match.group("paren_letter") or match.group("bare_letter")
 
        normalized = f"{prefix}-{digits}"
        if letter:
            normalized += f"({letter.upper()})"
 
        return normalized
 
    @classmethod
    def _extract_keywords(
        cls,
        query: str,
    ) -> list[str]:

        keywords: list[str] = []
        seen: set[str] = set()

        for match in cls.WORD.finditer(
            query.lower()
        ):

            word = match.group(0)

            if cls.ADMISSION_CODE.fullmatch(word):
                continue

            if word in cls.STOP_WORDS:
                continue

            if word not in seen:
                seen.add(word)
                keywords.append(word)

        return keywords
 
    @classmethod
    def _extract_phrases(
        cls,
        query: str,
    ) -> list[str]:

        phrases: list[str] = []
        seen: set[str] = set()

    # ------------------------------------------
    # Quoted phrases
    # ------------------------------------------

        for phrase in cls.PHRASE.findall(query):

            phrase = phrase.strip().lower()

            if phrase and phrase not in seen:
                seen.add(phrase)
                phrases.append(phrase)

    # ------------------------------------------
    # Build phrases from keywords
    # ------------------------------------------

        words = [
            word
            for word in cls._extract_keywords(query)
            if word not in {
                "of",
                "the",
                "a",
                "an",
                "for",
                "to",
                "in",
                "on",
                "and",
                "or",
                "with",
            }
        ]

    # Two-word phrases

        for i in range(len(words) - 1):

            phrase = f"{words[i]} {words[i+1]}"

            if phrase not in seen:
                seen.add(phrase)
                phrases.append(phrase)

    # Three-word phrases

        for i in range(len(words) - 2):

            phrase = (
                f"{words[i]} "
                f"{words[i+1]} "
                f"{words[i+2]}"
            )

            if phrase not in seen:
                seen.add(phrase)
                phrases.append(phrase)

        return phrases
    
    @classmethod
    def _extract_topics(
        cls,
        keywords: list[str],
        phrases: list[str],
    ) -> list[str]:

        topics: list[str] = []
        seen: set[str] = set()

        for word in keywords:
            if word in cls.TOPIC_KEYWORDS:
                if word not in seen:
                    seen.add(word)
                    topics.append(word)

        for phrase in phrases:
            phrase_words = phrase.split()

            if all(
                word in cls.TOPIC_KEYWORDS
                for word in phrase_words
            ):
                if phrase not in seen:
                    seen.add(phrase)
                    topics.append(phrase)

        return topics


    @classmethod
    def _extract_entities(
        cls,
        keywords: list[str],
        phrases: list[str],
        topics: list[str],
    ) -> list[str]:

        entities: list[str] = []
        seen: set[str] = set()

        topic_words = set()

        for topic in topics:
            topic_words.update(
                topic.split()
            )

        for phrase in phrases:

            phrase_words = phrase.split()

            if not phrase_words:
                continue

            if any(
                word in topic_words
                for word in phrase_words
            ):
                continue

            if len(phrase_words) < 2:
                continue

            if phrase not in seen:
                seen.add(phrase)
                entities.append(phrase)

        return entities