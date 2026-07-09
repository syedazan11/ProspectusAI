import re

from src.ingestion.extraction.models import TextQuality


class TextQualityAnalyzer:
    """
    Evaluates native PDF text extraction.

    The purpose is not to judge document content.
    It decides whether native extraction produced
    enough usable text to avoid OCR.
    """

    MIN_CHARACTERS = 40
    MIN_WORDS = 8
    MIN_ALPHANUMERIC_RATIO = 0.35
    MAX_REPLACEMENT_CHARACTERS = 5

    def analyze(self, text: str) -> TextQuality:
        normalized = text.strip()

        character_count = len(normalized)

        words = re.findall(
            r"\b[\w'-]+\b",
            normalized,
            flags=re.UNICODE,
        )
        word_count = len(words)

        if character_count:
            alphanumeric_count = sum(
                character.isalnum()
                for character in normalized
            )
            alphanumeric_ratio = (
                alphanumeric_count / character_count
            )
        else:
            alphanumeric_ratio = 0.0

        replacement_character_count = (
            normalized.count("\ufffd")
        )

        reasons: list[str] = []

        boilerplate_patterns = [
            r"ned university",
            r"undergraduate",
            r"prospectus\s+20\d{2}",
            r"engineering\s*&\s*technology",
            r"neduetofficial",
            r"neduet official",
            r"www\.neduet\.edu\.pk",
        ]

        boilerplate_matches = sum(
            bool(
                re.search(
                    pattern,
                    normalized,
                    flags=re.IGNORECASE,
                )
            )
            for pattern in boilerplate_patterns
        )

        boilerplate_only = (
            character_count < 350
            and boilerplate_matches >= 3
        )

        if boilerplate_only:
            reasons.append("boilerplate_only")

        if character_count < self.MIN_CHARACTERS:
            reasons.append("too_few_characters")

        if word_count < self.MIN_WORDS:
            reasons.append("too_few_words")

        if (
            character_count > 0
            and alphanumeric_ratio
            < self.MIN_ALPHANUMERIC_RATIO
        ):
            reasons.append(
                "low_alphanumeric_ratio"
            )

        if (
            replacement_character_count
            > self.MAX_REPLACEMENT_CHARACTERS
        ):
            reasons.append(
                "too_many_replacement_characters"
            )

        return TextQuality(
            character_count=character_count,
            word_count=word_count,
            alphanumeric_ratio=round(
                alphanumeric_ratio,
                4,
            ),
            replacement_character_count=(
                replacement_character_count
            ),
            is_usable=not reasons,
            reasons=reasons,
        )
