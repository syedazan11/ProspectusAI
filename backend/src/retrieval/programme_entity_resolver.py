import re
from collections import defaultdict
from typing import Any


class ProgrammeEntityResolver:
    """
    Resolve programme references from one active
    undergraduate prospectus.

    The resolver is document-specific. Its canonical
    programme identities come only from that document's
    curriculum records.

    It never silently chooses between colliding aliases.
    """

    DEGREE_PREFIXES = (
        "bachelor of engineering in ",
        "bachelor of engineering ",
        "bachelor of science in ",
        "bachelor of science ",
        "BE",
        "BS"
    )

    ALIAS_STOP_WORDS = {
        "and",
        "of",
        "in",
        "with",
        "the",
    }

    CONTEXT_GROUPS = {
        "tiest": {
            "tiest",
            "thar institute",
            "tharparkar",
        },
    }

    def __init__(
        self,
        *,
        curriculum_records: list[dict],
    ):
        self.programmes = (
            self._build_programmes(
                curriculum_records
            )
        )

        self.alias_index = (
            self._build_alias_index()
        )

    # def resolve(
    #     self,
    #     question: str,
    # ) -> list[dict]:
    #     normalized_question = self._normalize(
    #         question
    #     )

    #     if not normalized_question:
    #         return []

    #     exact_matches = (
    #         self._canonical_name_matches(
    #             normalized_question
    #         )
    #     )

    #     if exact_matches:
    #         exact_matches = (
    #             self._apply_context_disambiguation(
    #                 question=normalized_question,
    #                 matches=exact_matches,
    #             )
    #         )

    #         return self._deduplicate(
    #             exact_matches
    #         )

    #     alias_matches = self._alias_matches(
    #         question=question,
    #         normalized_question=normalized_question,
    #     )

    #     if not alias_matches:
    #         return []

    #     alias_matches = (
    #         self._apply_context_disambiguation(
    #             question=normalized_question,
    #             matches=alias_matches,
    #         )
    #     )

    #     return self._deduplicate(
    #         alias_matches
    #     )

    # def resolve(
    #     self,
    #     question: str,
    # ) -> list[dict]:

    #     normalized_question = self._normalize(question)

    #     if not normalized_question:
    #         return []

    #     # Collect BOTH canonical and alias matches.
    #     matches = []

    #     matches.extend(
    #         self._canonical_name_matches(
    #             normalized_question
    #         )
    #     )

    #     matches.extend(
    #         self._alias_matches(
    #             question=question,
    #             normalized_question=normalized_question,
    #         )
    #     )

    #     matches = self._deduplicate(matches)

    #     if not matches:
    #         return []

    #     matches = self._apply_context_disambiguation(
    #         question=normalized_question,
    #         matches=matches,
    #     )

    #     return self._deduplicate(matches)

    def resolve(
        self,
        question: str,
    ) -> list[dict]:

        normalized_question = self._normalize(
            question
        )

        if not normalized_question:
            return []

        # # Prefer explicit canonical programme names.
        # # If the question contains a specific programme name,
        # # do not let shorter aliases create unrelated matches.
        # canonical_matches = (
        #     self._canonical_name_matches(
        #         normalized_question
        #     )
        # )

        # if canonical_matches:

        #     canonical_matches = (
        #         self._apply_context_disambiguation(
        #             question=normalized_question,
        #             matches=canonical_matches,
        #         )
        #     )

        #     return self._prefer_longest(
        #         canonical_matches
        #     )
        # Collect canonical and alias matches together.
        # This is important when one programme uses a full
        # degree title and another uses a shortened title.
        matches = []

        matches.extend(
            self._canonical_name_matches(
                normalized_question
            )
        )

        matches.extend(
            self._alias_matches(
                question=question,
                normalized_question=normalized_question,
            )
        )

        matches = self._deduplicate(matches)

        if matches:
            matches = self._apply_context_disambiguation(
                question=normalized_question,
                matches=matches,
            )

            return self._deduplicate(matches)

        # No canonical programme name was found.
        # Fall back to aliases and abbreviations.
        alias_matches = self._alias_matches(
            question=question,
            normalized_question=normalized_question,
        )

        if alias_matches:
            alias_matches = (
                self._apply_context_disambiguation(
                    question=normalized_question,
                    matches=alias_matches,
                )
            )

            return self._deduplicate(
                alias_matches
            )

# Natural shortened programme name.

        print(
            "[RESOLVER SUBSET DEBUG]",
            normalized_question,
        )
        subset_matches = self._token_subset_matches(
            normalized_question,
        )

        print(
            "[RESOLVER SUBSET RESULT]",
            subset_matches,
        )

        if not subset_matches:
            return []

        subset_matches = (
            self._apply_context_disambiguation(
                question=normalized_question,
                matches=subset_matches,
            )
        )

        return self._deduplicate(
            subset_matches
        )



    def _build_programmes(
        self,
        curriculum_records: list[dict],
    ) -> list[dict]:
        unique = {}

        for record in curriculum_records:
            code = str(
                record.get(
                    "programme_code",
                    "",
                )
            ).strip()

            name = str(
                record.get(
                    "programme",
                    "",
                )
            ).strip()

            parent = str(
                record.get(
                    "parent_section",
                    "",
                )
                or ""
            ).strip()

            if not code or not name:
                continue

            key = (
                code,
                name,
                parent,
            )

            unique[key] = {
                "programme_code": code,
                "programme": name,
                "parent_section": parent,
            }

        return list(
            unique.values()
        )

    def _build_alias_index(
        self,
    ) -> dict[str, list[dict]]:
        index = defaultdict(list)

        for programme in self.programmes:
            aliases = (
                self._programme_aliases(
                    programme
                )
            )

            for alias in aliases:
                index[alias].append(
                    programme
                )

        return dict(index)

    def _programme_aliases(
        self,
        programme: dict,
    ) -> set[str]:
        name = programme["programme"]

        normalized_name = self._normalize(
            name
        )

        core = self._programme_core(
            name
        )

        base_programme = re.split(
            r"\bwith\s+speciali[sz]ation\b",
            core,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip()

        aliases = {
            normalized_name,
            core,
        }

        if base_programme:
            aliases.add(
                self._normalize(base_programme)
            )

        initialism = self._initialism(
            core
        )

        if initialism:
            aliases.add(
                self._normalize(initialism)
            )

        return {
            alias
            for alias in aliases
            if alias
        }

    def _canonical_name_matches(
        self,
        normalized_question: str,
    ) -> list[dict]:
        matches = []

        for programme in self.programmes:
            name = self._normalize(
                programme["programme"]
            )

            if self._contains_phrase(
                normalized_question,
                name,
            ):
                matches.append(
                    programme
                )

        return matches

    def _token_subset_matches(
        self,
        normalized_question: str,
    ) -> list[dict]:

        normalized_question = re.sub(
            r"\b\d+(?:st|nd|rd|th)?\s+(?:semester|year)\b",
            " ",
            normalized_question,
        )

        question_tokens = set(
            normalized_question.split()
        )

        # Common natural abbreviations.
        if "eng" in question_tokens:
            question_tokens.add("engineering")
    
        if "sci" in question_tokens:
            question_tokens.add("science")
    
        if "tech" in question_tokens:
            question_tokens.add("technology")

    # Ignore words that are not useful for identifying
    # a programme.
        ignored = {
            "what",
            "are",
            "is",
            "the",
            "courses",
            "course",
            "subjects",
            "subject",
            "semester",
            "year",
            "of",
            "in",
            "for",
            "this",
            "that",
            "first",
            "second",
            "third",
            "fourth",
            "final",
        }

        question_tokens -= ignored

        print(
            "[RESOLVER QUESTION TOKENS]",
            question_tokens,
        )

        if len(question_tokens) < 2:
            return []

        candidates = []

        print(
            "[RESOLVER PROGRAMMES]",
            [
                (
                    p.get("programme"),
                    p.get("programme_code"),
                )
                for p in self.programmes
            ],
        )

        for programme in self.programmes:

            programme_tokens = set(
                self._normalize(
                    programme["programme"]
                ).split()
            )

            if not question_tokens.issubset(
                programme_tokens
            ):
                continue

            candidates.append(programme)

        return self._deduplicate(candidates)

    def _alias_matches(
        self,
        *,
        question: str,
        normalized_question: str,
    ) -> list[dict]:
        matched = []

        uppercase_tokens = {
            self._normalize(token)
            for token in re.findall(
                r"(?<![A-Za-z0-9])"
                r"[A-Z][A-Z0-9]{1,9}"
                r"(?![A-Za-z0-9])",
                question,
            )
        }

        for alias, programmes in (
            self.alias_index.items()
        ):
            is_short_alias = (
                " " not in alias
                and len(alias) <= 10
            )

            if is_short_alias:
                is_explicit_uppercase = (
                    alias in uppercase_tokens
                )

                is_present_lowercase = (
                    self._contains_phrase(
                        normalized_question,
                        alias,
                    )
                )

                canonical_names = {
                    self._normalize(
                        programme.get(
                            "programme",
                            "",
                        )
                    )
                    for programme in programmes
                    if programme.get(
                        "programme"
                    )
                }

                is_safe_lowercase_alias = (
                    is_present_lowercase
                    and len(canonical_names) == 1
                )

                if not (
                    is_explicit_uppercase
                    or is_safe_lowercase_alias
                ):
                    continue

            elif not self._contains_phrase(
                normalized_question,
                alias,
            ):
                continue

            matched.extend(
                programmes
            )

        return matched

    def _apply_context_disambiguation(
        self,
        *,
        question: str,
        matches: list[dict],
    ) -> list[dict]:
        if len(matches) <= 1:
            return matches

        for context_name, terms in (
            self.CONTEXT_GROUPS.items()
        ):
            has_context = any(
                self._contains_phrase(
                    question,
                    self._normalize(term),
                )
                for term in terms
            )

            if not has_context:
                continue

            contextual = [
                item
                for item in matches
                if self._contains_phrase(
                    self._normalize(
                        item.get(
                            "parent_section",
                            "",
                        )
                    ),
                    context_name,
                )
                or any(
                    self._contains_phrase(
                        self._normalize(
                            item.get(
                                "parent_section",
                                "",
                            )
                        ),
                        self._normalize(term),
                    )
                    for term in terms
                )
            ]

            if contextual:
                return contextual

        return matches

    def _prefer_longest(
        self,
        matches: list[dict],
    ) -> list[dict]:
        if not matches:
            return []

        longest = max(
            len(
                self._normalize(
                    item["programme"]
                )
            )
            for item in matches
        )

        return self._deduplicate(
            [
                item
                for item in matches
                if len(
                    self._normalize(
                        item["programme"]
                    )
                )
                == longest
            ]
        )

    @classmethod
    def _programme_core(
        cls,
        value: str,
    ) -> str:
        text = cls._normalize(value)

        for prefix in cls.DEGREE_PREFIXES:
            if text.startswith(prefix):
                return text[
                    len(prefix):
                ].strip()

        return text

    @classmethod
    def _initialism(
        cls,
        value: str,
    ) -> str | None:
        words = [
            word
            for word in cls._normalize(
                value
            ).split()
            if (
                word
                not in cls.ALIAS_STOP_WORDS
            )
        ]

        if len(words) < 2:
            return None

        return "".join(
            word[0]
            for word in words
            if word
        )

    @staticmethod
    def _contains_phrase(
        text: str,
        phrase: str,
    ) -> bool:
        if not phrase:
            return False

        return bool(
            re.search(
                r"(?<![a-z0-9])"
                + re.escape(phrase)
                + r"(?![a-z0-9])",
                text,
            )
        )

    @staticmethod
    def _deduplicate(
        matches: list[dict],
    ) -> list[dict]:
        unique = {}

        for item in matches:
            key = (
                item["programme_code"],
                item["programme"],
                item.get(
                    "parent_section",
                    "",
                ),
            )

            unique[key] = item

        return list(
            unique.values()
        )

    @staticmethod
    def _normalize(
        value: Any,
    ) -> str:
        text = str(value).casefold()

        text = text.replace(
            "&",
            " and ",
        )

        text = re.sub(
            r"\bspecialisation\b",
            "specialization",
            text,
        )

        text = re.sub(
            r"[^a-z0-9]+",
            " ",
            text,
        )

        return re.sub(
            r"\s+",
            " ",
            text,
        ).strip()
