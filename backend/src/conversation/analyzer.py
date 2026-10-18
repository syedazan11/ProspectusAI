from __future__ import annotations
from email import message
import re
from .models import ConversationDecision, ConversationTopic, ConversationTransition
from .state import ConversationState


class ConversationAnalyzer:
    """
    Responsible for understanding a user's message before
    retrieval or answer generation.

    It never calls the retriever or the LLM.
    It only classifies the request and returns a
    ConversationDecision.
    """

    def __init__(
        self,
    ):

        from .context_resolver import ContextResolver

        self._resolver = ContextResolver()

    def _extract_user_name(
        self,
        message: str,
    ) -> str | None:

        patterns = (
            r"\bmy name is ([A-Za-z ]{2,40})",
            r"\bi am ([A-Za-z ]{2,40})",
            r"\bi'm ([A-Za-z ]{2,40})",
            r"\bcall me ([A-Za-z ]{2,40})",
        )

        for pattern in patterns:

            match = re.search(
                pattern,
                message,
                flags=re.IGNORECASE,
            )

            if match:

                return match.group(1).strip()

        return None

    def analyze(
        self,
        message: str,
        state: ConversationState,
    ) -> ConversationDecision:

        normalized = self._normalize(message)

        intent = self._detect_intent(
            normalized,
        )

        domain = self._detect_domain(
            normalized,
            intent,
        )        

        quality = self._detect_quality(
            normalized,
        )

        topic = self._extract_topic(
            normalized,
        )

        transition = self._detect_transition(
            topic=topic,
            domain=domain,
            state=state,
        )

        decision = self._build_decision(
            message=message,
            normalized=normalized,
            intent=intent,
            domain=domain,
            quality=quality,
            topic=topic,
            transition=transition,
            state=state,
        )

        name = self._extract_user_name(
            normalized,
        )

        if name:
            state.user_name = name

        state.update(
            message=normalized,
            action=decision.action,
            topic=topic,
        )

        return decision

        # return self._build_decision(
        #     message=message,
        #     normalized=normalized,
        #     intent=intent,
        #     domain=domain,
        #     quality=quality,
        #     state=state,
        #     topic=topic,
        # )

    def _normalize(
        self,
        message: str,
    ) -> str:
        """
        Normalize a user message before analysis.

        This method intentionally preserves meaning while removing
        superficial formatting differences.
        """

        text = message.strip()

        # collapse whitespace
        text = re.sub(
            r"\s+",
            " ",
            text,
        )

    # collapse repeated punctuation
        text = re.sub(
            r"([!?.,])\1+",
            r"\1",
            text,
        )

        return text

    def _detect_intent(
        self,
        message: str,
    ):

        text = message.casefold()

        greeting_words = {
            "hi",
            "hello",
            "hey",
            "assalam",
            "assalamu alaikum",
            "salam",
            "good morning",
            "good afternoon",
            "good evening",
        }

        goodbye_words = {
            "bye",
            "goodbye",
            "see you",
            "take care",
            "allah hafiz",
        }

        thanks_words = {
            "thanks",
            "thank you",
            "thx",
            "jazakallah",
        }

        introduction_words = {
            "who are you",
            "introduce yourself",
            "what are you",
            "your name",
        }

        capability_words = {
            "what can you do",
            "help me",
            "how can you help",
            "your capabilities",
            "what do you do",
        }

        for phrase in greeting_words:
            if phrase in text:
                return "greeting"

        for phrase in goodbye_words:
            if phrase in text:
                return "goodbye"

        for phrase in thanks_words:
            if phrase in text:
                return "thanks"

        for phrase in introduction_words:
            if phrase in text:
                return "introduction"

        for phrase in capability_words:
            if phrase in text:
                return "capability"

        return "unknown"

    def _detect_domain(
        self,
        message: str,
        intent: str,
    ) -> str:

        if intent != "unknown":
            return "conversation"

        text = message.casefold()

        words = re.findall(
            r"[a-z0-9]+",
            text,
        )

        if not words:
            return "unknown"

        prospectus_score = 0
        external_score = 0

        prospectus_terms = {
            "admission",
            "apply",
            "application",
            "department",
            "faculty",
            "programme",
            "program",
            "course",
            "curriculum",
            "semester",
            "credit",
            "fee",
            "fees",
            "eligibility",
            "criteria",
            "hostel",
            "scholarship",
            "seat",
            "quota",
            "category",
            "chairperson",
            "co chairperson",
            "chancellor",
            "vice chancellor",
            "director",
            "dean",
            "professor",
            "lecturer",
            "campus",
            "transport",
            "library",
            "laboratory",
            "IT",
            "information technology",
            "computer",
            "science",
            "engineering",
            "arts",
            "humanities",
            "lecturer",
            "assistant",
            "associate",
            "professor",
            "faculty",
            "department",
            "program",
            "programme",
            "course",
            "curriculum",
            "semester",
            "credit",
            "fee",
            "fees",
            
        }

        external_terms = {
            "capital",
            "country",
            "weather",
            "temperature",
            "football",
            "cricket",
            "instagram",
            "facebook",
            "youtube",
            "movie",
            "song",
            "actor",
            "president",
            "prime",
            "minister",
            "earthquake",
            "bitcoin",
            "stock",
            "ipl",
            "fifa",
        }

        for word in words:

            if word in prospectus_terms:
                prospectus_score += 2

            if word in external_terms:
                external_score += 2

        if prospectus_score > external_score and prospectus_score >= 2:
            return "prospectus"

        if external_score > prospectus_score and external_score >= 2:
            return "external"

        return "unknown"

    def _detect_transition(
        self,
        *,
        topic: ConversationTopic,
        domain: str,
        state: ConversationState,
    ) -> ConversationTransition:

        if domain == "conversation":
            return ConversationTransition.CONVERSATION

        if domain == "external":
            return ConversationTransition.OUT_OF_DOMAIN

        if state.topic is None:
            return ConversationTransition.NEW_TOPIC

        previous = state.topic

        previous_entities = {
            entity.casefold()
            for entity in previous.entities
        }

        current_entities = {
            entity.casefold()
            for entity in topic.entities
        }

        if (
            current_entities
            and current_entities == previous_entities
        ):
            return ConversationTransition.SAME_TOPIC

        if (
            not current_entities
            and previous_entities
            and topic.subject is not None
        ):
            return ConversationTransition.FOLLOW_UP

        if (
            current_entities
            and previous_entities
            and current_entities != previous_entities
        ):
            return ConversationTransition.NEW_TOPIC

        return ConversationTransition.NEW_TOPIC

    def _detect_quality(
        self,
        message: str,
    ) -> str:

        text = message.strip()

        if not text:
            return "empty"

        if len(text) < 2:
            return "gibberish"

        letters = re.findall(
            r"[A-Za-z]",
            text,
        )

        digits = re.findall(
            r"\d",
            text,
        )

        words = re.findall(
            r"[A-Za-z]+",
            text,
        )

        # Only punctuation
        if not letters and not digits:
            return "gibberish"

        # Extremely long random token
        if (
            len(words) == 1
            and len(words[0]) >= 12
        ):
            vowels = sum(
                c in "aeiouAEIOU"
                for c in words[0]
            )

            if vowels <= 1:
                return "gibberish"

        # Keyboard smash
        keyboard_patterns = (
            "asdf",
            "qwer",
            "zxcv",
            "hjkl",
        )

        lowered = text.casefold()

        if any(
            pattern in lowered
            for pattern in keyboard_patterns
        ):
            return "gibberish"

        return "normal"

    def _extract_topic(
        self,
        message: str,
    ) -> ConversationTopic:

        text = message.casefold()

        words = re.findall(
            r"[a-z0-9][a-z0-9&+.-]*",
            text,
        )

        stop_words = {
            "what",
            "who",
            "is",
            "the",
            "of",
            "for",
            "in",
            "about",
            "tell",
            "show",
            "me",
            "please",
            "give",
            "can",
            "you",
            "does",
            "do",
        }

        entities = []

        for word in words:

            if len(word) <= 2:
                continue

            if word in stop_words:
                continue

            entities.append(word)

        subject = None

        subject_words = (
            "fee",
            "fees",
            "eligibility",
            "curriculum",
            "chairperson",
            "co chairperson",
            "chancellor",
            "vice chancellor",
            "director",
            "dean",
            "hostel",
            "transport",
            "scholarship",
            "seat",
            "quota",
            "faculty",
            "department",
            "programme",
            "program",
            "course",
            "semester",
            "credit",
            "admission",
            "application",
            "apply",
            "eligibility",
            "criteria",    
        )

        for word in words:

            if word in subject_words:
                subject = word
                break

        codes = re.findall(
            r"(?:R|SF)-\d+(?:\([A-Za-z0-9]+\))?",
            message,
            flags=re.IGNORECASE,
        )

        return ConversationTopic(
            entities=list(dict.fromkeys(entities)),
            subject=subject,
            codes=codes,
        )

    
    def _build_decision(
        self,
        *,
        message: str,
        normalized: str,
        intent,
        domain,
        quality: str,
        state: ConversationState,
        transition: ConversationTransition,
    ) -> ConversationDecision:

        if quality == "empty":
            return ConversationDecision(
                action="empty",
                requires_retrieval=False,
                transition=transition,
            )

        if quality == "gibberish":
            return ConversationDecision(
                action="gibberish",
                requires_retrieval=False,
                transition=transition,
            )

        if intent == "greeting":
            return ConversationDecision(
                action="greeting",
                requires_retrieval=False,
                transition=transition,
            )


        if intent == "goodbye":
            return ConversationDecision(
                action="goodbye",
                requires_retrieval=False,
                transition=transition,
            )

        if intent == "thanks":
            return ConversationDecision(
                action="thanks",
                requires_retrieval=False,
                transition=transition,
            )

        if intent == "introduction":
            return ConversationDecision(
                action="introduction",
                requires_retrieval=False,
                transition=transition,
            )

        if intent == "capability":
            return ConversationDecision(
                action="capability",
                requires_retrieval=False,
                transition=transition,
            )
        
        if domain == "external":
            return ConversationDecision(
                action="out_of_domain",
                requires_retrieval=False,
                transition=transition,
            )

        if domain == "prospectus":
            return ConversationDecision(
                action="retrieve",
                requires_retrieval=True,
                transition=transition,
            )

        return ConversationDecision(
            action="unknown",
            requires_retrieval=False,
            transition=transition,
        )
