from __future__ import annotations

import re


class NameDetector:

    TITLES = {
        "dr",
        "prof",
        "engr",
        "eng",
        "mr",
        "mrs",
        "ms",
        "miss",
        "sir",
    }

    QUESTION_PREFIXES = (
        "who is ",
        "who's ",
        "tell me about ",
        "information about ",
        "details about ",
    )

    # Words that strongly indicate the text is a normal
    # prospectus/domain query rather than a person's name.
    NON_NAME_WORDS = {
        "bachelor",
        "master",
        "degree",
        "engineering",
        "computer",
        "science",
        "software",
        "electrical",
        "electronic",
        "mechanical",
        "civil",
        "chemical",
        "industrial",
        "telecommunication",
        "architecture",
        "program",
        "programme",
        "programmes",
        "course",
        "courses",
        "semester",
        "admission",
        "admissions",
        "eligibility",
        "criteria",
        "requirement",
        "requirements",
        "fee",
        "fees",
        "faculty",
        "staff",
        "department",
        "departments",
        "chairperson",
        "professor",
        "lecturer",
        "manager",
        "campus",
        "hostel",
        "scholarship",
        "scholarships",
        "facility",
        "facilities",
        "laboratory",
        "laboratories",
        "lab",
        "labs",
        "contact",
        "location",
        "deadline",
        "deadlines",
    }

    @classmethod
    def is_person_name(cls, query: str) -> bool:
        text = query.strip()

        if not text:
            return False

        # Remove trailing punctuation.
        text = re.sub(r"[?!.]+$", "", text).strip()

        lowered = text.casefold()

        # Remove natural-language question prefixes.
        for prefix in cls.QUESTION_PREFIXES:
            if lowered.startswith(prefix):
                text = text[len(prefix):].strip()
                break

        words = text.split()

        if not words:
            return False

        # Remove one or more consecutive professional titles.
        has_title = False

        while words:
            first_word = words[0].rstrip(".").casefold()

            if first_word not in cls.TITLES:
                break

            has_title = True
            words.pop(0)

        if not words or len(words) > 6:
            return False

        # A bare single word is too ambiguous to identify as a person.
        if not has_title and len(words) < 2:
            return False

        # Every remaining token must look like a name component.
        for word in words:
            cleaned = word.strip(".,")
            if not re.fullmatch(
                r"[A-Za-z][A-Za-z'-]*",
                cleaned,
            ):
                return False

        # Reject obvious prospectus/domain terminology.
        for word in words:
            if word.casefold() in cls.NON_NAME_WORDS:
                return False

        return True