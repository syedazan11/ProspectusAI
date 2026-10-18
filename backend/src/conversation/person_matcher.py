from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PersonMatch:
    name: str
    record: dict


class PersonMatcher:
    TITLES = {
        "dr",
        "Dr",
        "prof",
        "Prof",
        "engr",
        "Engr",
        "mr",
        "Mr",
        "mrs",
        "Mrs",
        "ms",
        "Ms",
        "miss",
        "Miss",
        "sir",
        "Sir",
    }

    QUERY_PREFIXES = (
        "who is ",
        "who's ",
        "tell me about ",
        "information about ",
        "details about ",
        "department of ",
        "dep of ",
        "qualifications of ",
        "role of ",
        "designation of ",  
        "do you know about ",
    )

    QUERY_SUFFIXES = (
        " department",
        " qualifications",
        " role",
        " designation",
        " position",
    )

    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.casefold()
        value = re.sub(r"[.,]", " ", value)

        words = value.split()

        # Remove professional titles so:
        # "Dr. Ali Naqvi" == "Engr. Ali Naqvi"
        words = [
            word
            for word in words
            if word not in cls.TITLES
        ]

        return " ".join(words)

    @classmethod
    def extract_person_query(cls, query: str) -> str:
        text = query.strip()
        lowered = text.casefold()

        for prefix in cls.QUERY_PREFIXES:
            if lowered.startswith(prefix):
                return text[len(prefix):].strip(" ?.")

        for suffix in cls.QUERY_SUFFIXES:
            if lowered.endswith(suffix):
                return text[: -len(suffix)].strip(" ?.")

        return text.strip(" ?.")


    @classmethod
    def extract_requested_name(
        cls,
        query: str,
        *,
        people_intent: bool,
    ) -> str | None:
        """Extract a specific person's name without requiring an indexed match."""
        if people_intent:
            return None

        if not cls.is_person_query(query):
            return None

        candidate = cls.extract_person_query(query).strip()

        if not candidate:
            return None

        normalized_candidate = cls.normalize_name(candidate)

        # Reject pronouns and single-word candidates.
        if len(normalized_candidate.split()) < 2:
            return None

        return candidate


    @staticmethod
    def _is_contiguous_name_match(
        query: str,
        name: str,
    ) -> bool:
        query_tokens = query.split()
        name_tokens = name.split()

        if not query_tokens:
            return False

        if len(query_tokens) > len(name_tokens):
            return False

        query_length = len(query_tokens)

        return any(
            name_tokens[index:index + query_length]
            == query_tokens
            for index in range(
                len(name_tokens) - query_length + 1
            )
        )


    @classmethod
    def extract_record_name(cls, content: str) -> str | None:
        """Extract the value belonging to the structured Name: field."""
        lines = [line.strip() for line in content.splitlines()]

        for index, line in enumerate(lines):
            if line.casefold() != "name:":
                continue

            if index + 1 >= len(lines):
                return None

            name = lines[index + 1].strip()
            return name or None

        return None

    @classmethod
    def names_match(
        cls,
        requested_name: str,
        record_name: str,
    ) -> bool:
        """Match normalized names as contiguous token sequences."""
        normalized_requested = cls.normalize_name(requested_name)
        normalized_record = cls.normalize_name(record_name)

        if not normalized_requested or not normalized_record:
            return False

        return cls._is_contiguous_name_match(
            normalized_requested,
            normalized_record,
        )


    @classmethod
    def find_matches(
        cls,
        query: str,
        people_records: list[dict],
    ) -> list[PersonMatch]:

        person_query = cls.extract_person_query(query)
        normalized_query = cls.normalize_name(person_query)

        if not normalized_query:
            return []

        matches: list[PersonMatch] = []

        for record in people_records:
            if record.get("record_type") != "people":
                continue

            content = record.get("content", "")
            lines = [line.strip() for line in content.splitlines()]

            for index, line in enumerate(lines):
                if line.casefold() != "name:":
                    continue

                if index + 1 >= len(lines):
                    continue

                name = lines[index + 1].strip()

                if not name:
                    continue

                normalized_name = cls.normalize_name(name)

##changes made 16 oct
                # if (
                #     normalized_query == normalized_name
                #     or normalized_query in normalized_name
                #     or normalized_name in normalized_query
                # ):
                if cls._is_contiguous_name_match(
                    normalized_query,
                    normalized_name,
                ):
                    matches.append(
                        PersonMatch(
                            name=name,
                            record=record,
                        )
                    )

                break

        # Remove duplicate records.
        unique: dict[str, PersonMatch] = {}

        for match in matches:
            key = cls.normalize_name(match.name)

            if key not in unique:
                unique[key] = match

        return list(unique.values())

    @classmethod
    def match_status(
        cls,
        query: str,
        people_records: list[dict],
    ) -> tuple[str, list[PersonMatch]]:
        matches = cls.find_matches(query, people_records)

        if not matches:
            return "none", []

        if len(matches) == 1:
            return "unique", matches

        return "ambiguous", matches

    @classmethod
    def exact_name_status(
        cls,
        query: str,
        people_records: list[dict],
    ) -> tuple[str, list[PersonMatch]]:

        normalized_query = cls.normalize_name(query)

        if not normalized_query:
            return "none", []

        matches: list[PersonMatch] = []

        for record in people_records:
            if record.get("record_type") != "people":
                continue

            content = record.get("content", "")
            lines = [line.strip() for line in content.splitlines()]

            for index, line in enumerate(lines):
                if line.casefold() != "name:":
                    continue

                if index + 1 >= len(lines):
                    continue

                name = lines[index + 1].strip()

                if (
                    name
                    and cls.normalize_name(name)
                    == normalized_query
                ):
                    matches.append(
                        PersonMatch(
                            name=name,
                            record=record,
                        )
                    )

                break

        if not matches:
            return "none", []

        if len(matches) == 1:
            return "unique", matches

        return "ambiguous", matches

    @classmethod
    def partial_name_status(
        cls,
        query: str,
        people_records: list[dict],
    ) -> tuple[str, list[PersonMatch]]:

        normalized_query = cls.normalize_name(query)

        if not normalized_query:
            return "none", []

        query_tokens = set(normalized_query.split())

        # A partial name must contain at least two tokens.
        if len(query_tokens) < 2:
            return "none", []

        matches: list[PersonMatch] = []

        for record in people_records:
            if record.get("record_type") != "people":
                continue

            content = record.get("content", "")
            lines = [line.strip() for line in content.splitlines()]

            for index, line in enumerate(lines):
                if line.casefold() != "name:":
                    continue

                if index + 1 >= len(lines):
                    continue

                name = lines[index + 1].strip()

                if not name:
                    continue

                normalized_name = cls.normalize_name(name)
                name_tokens = set(normalized_name.split())

                if query_tokens.issubset(name_tokens):
                    matches.append(
                        PersonMatch(
                            name=name,
                            record=record,
                        )
                    )

                break

        unique: dict[str, PersonMatch] = {}

        for match in matches:
            key = cls.normalize_name(match.name)

            if key not in unique:
                unique[key] = match

        if not unique:
            return "none", []

        if len(unique) == 1:
            return "unique", list(unique.values())

        return "ambiguous", list(unique.values())

    @classmethod
    def is_person_query(cls, query: str) -> bool:
        text = query.strip()
        if not text:
            return False

        lowered = text.casefold()

        prefixes = (
            "who is ",
            "who's ",
            "whos",
            "tell me about ",
            "information about ",
            "details about ",
            "department of ",
            "dep of ",
            "qualifications of ",
            "what department is ",
            # "what are ",
            # "what does ",
            "does ",
            "where does ",
            # "is ",
        )

        suffixes = (
            " department",
            " qualifications",
            " role",
            " designation",
            " position",
        )

        if any(lowered.startswith(prefix) for prefix in prefixes):
            return True

        if any(lowered.endswith(suffix) for suffix in suffixes):
            return True

        # Name-only queries are handled by the actual record matcher.
        # Keep this conservative so arbitrary gibberish is not forced
        # into the person-query path.
        return False