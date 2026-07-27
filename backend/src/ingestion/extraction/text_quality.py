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
    MAX_NEWLINE_RATIO = 0.25
    MAX_SINGLE_WORD_LINE_RATIO = 0.60
    MAX_AVERAGE_WORD_LENGTH = 20

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

        punctuation_count = sum(
            not character.isalnum() and not character.isspace()
            for character in normalized
        )

        punctuation_ratio = (
            punctuation_count / character_count
            if character_count > 0
            else 0.0
        )

        unique_words = len(
            {
                word.lower()
                for word in words
            }
        )

        vocabulary_ratio = (
            unique_words / word_count
            if word_count > 0
            else 0.0
        )

        lines = [
            line.strip()
            for line in normalized.splitlines()
            if line.strip()
        ]

        line_count = len(lines)

        newline_ratio = (
            line_count / word_count
            if word_count > 0
            else 0.0
        )

        single_word_lines = sum(
            len(
                re.findall(
                    r"\b[\w'-]+\b",
                    line,
                    flags=re.UNICODE,
                )
            ) == 1
            for line in lines
        )

        single_word_line_ratio = (
            single_word_lines / line_count
            if line_count > 0
            else 0.0
        )

        average_word_length = (
            sum(len(word) for word in words)
            / word_count
            if word_count > 0
            else 0.0
        )

        reasons: list[str] = []
        warnings: list[str] = []

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

        if newline_ratio > self.MAX_NEWLINE_RATIO:
            warnings.append(
                "excessive_line_breaks"
            )

        if (
            single_word_line_ratio
            > self.MAX_SINGLE_WORD_LINE_RATIO
        ):
            warnings.append(
                "fragmented_text"
            )

        if (
            average_word_length
            > self.MAX_AVERAGE_WORD_LENGTH
        ):
            warnings.append(
                "abnormal_word_length"
            )

        if punctuation_ratio > 0.35:
            warnings.append(
                "excessive_punctuation"
            )

        if (
            word_count >= 20
            and vocabulary_ratio < 0.20
        ):
            warnings.append(
                "highly_repetitive_text"
            )

        if warnings:
            print(
                f"[QUALITY WARNING] "
                f"chars={character_count} "
                f"words={word_count} "
                f"warnings={warnings}"
            )

        if reasons:
            print(
                f"[QUALITY FAILURE] "
                f"chars={character_count} "
                f"words={word_count} "
                f"reasons={reasons}"
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
            warnings=warnings,
    )
