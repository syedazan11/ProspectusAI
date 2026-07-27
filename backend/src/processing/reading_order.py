from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from enum import Enum, auto
import re


class LineType(Enum):
    EMPTY = auto()
    NUMBER = auto()
    ROLE = auto()
    PERSON = auto()
    QUALIFICATION = auto()
    HEADING = auto()
    FOOTER = auto()
    URL = auto()
    PARAGRAPH = auto()


@dataclass(slots=True)
class ClassifiedLine:
    text: str
    line_type: LineType


class ReadingOrderRepairService:
    """
    Generic reading-order analysis.

    Phase 1:
      - classify every line
      - do not reorder anything
    """

    ROLE_PATTERN = re.compile(
        r"^(?:"
        r"Chairperson|"
        r"Co[- ]?Chairperson|"
        r"Chairman|"
        r"Dean|"
        r"Director|"
        r"Registrar|"
        r"Vice[- ]?Chancellor|"
        r"Pro[- ]?Vice[- ]?Chancellor|"
        r"Professor(?:s)?|"
        r"Associate Professor(?:s)?|"
        r"Assistant Professor(?:s)?|"
        r"Lecturer(?:s)?"
        r")$",
        re.IGNORECASE,
    )

    TITLE_PATTERN = re.compile(
        r"^(?:Prof\.?|Dr\.?|Mr\.?|Mrs\.?|Ms\.?|Engr\.?)",
        re.IGNORECASE,
    )

    QUALIFICATION_PATTERN = re.compile(
        r"\b("
        r"B\.?E\.?|"
        r"B\.?Sc\.?|"
        r"B\.?S\.?|"
        r"M\.?E\.?|"
        r"M\.?Sc\.?|"
        r"M\.?S\.?|"
        r"MBA|"
        r"M\.?Phil|"
        r"Ph\.?D"
        r")\b",
        re.IGNORECASE,
    )

    def classify(self, line: str) -> ClassifiedLine:

        text = line.strip()

        if not text:
            return ClassifiedLine(text, LineType.EMPTY)

        if text.isdigit():
            return ClassifiedLine(text, LineType.NUMBER)

        if text.lower().startswith("www."):
            return ClassifiedLine(text, LineType.URL)

        if self.ROLE_PATTERN.fullmatch(text):
            return ClassifiedLine(text, LineType.ROLE)

        if self.TITLE_PATTERN.match(text):
            return ClassifiedLine(text, LineType.PERSON)

        if self.QUALIFICATION_PATTERN.search(text):
            return ClassifiedLine(text, LineType.QUALIFICATION)

        return ClassifiedLine(text, LineType.PARAGRAPH)
    
    def classify_page(
        self,
        lines: list[str],
    ) -> list[ClassifiedLine]:

        classified: list[ClassifiedLine] = []

        for line in lines:
            classified.append(
                self.classify(line)
            )

        return classified
    

    def analyze_page(
        self,
        lines: list[str],
    ) -> dict:

        classified = self.classify_page(lines)
        sequence_score = 0

        previous = None

        for item in classified:

            sequence_score += self._transition_score(
                previous,
                item.line_type,
            )

            previous = item.line_type

        counts = Counter(
            item.line_type
            for item in classified
        )

        role_runs = 0
        previous = None

        for item in classified:

            if (
                item.line_type == LineType.ROLE
                and previous == LineType.ROLE
            ):
                role_runs += 1

            previous = item.line_type

        suspicious = (
            role_runs >= 2
            or counts[LineType.ROLE] >= 4
        )

        return {
            "classified": classified,
            "role_runs": role_runs,
            "counts": counts,
            "sequence_score": sequence_score,
            "suspicious": suspicious,
        }
    
    def _transition_score(
        self,
        previous: LineType | None,
        current: LineType,
    ) -> int:

        if previous is None:
            return 0

        transitions = {

            (LineType.ROLE, LineType.PERSON): 6,
            (LineType.PERSON, LineType.QUALIFICATION): 5,
            (LineType.QUALIFICATION, LineType.QUALIFICATION): 3,
            (LineType.QUALIFICATION, LineType.PERSON): 4,
            (LineType.PERSON, LineType.PERSON): 2,
            (LineType.ROLE, LineType.ROLE): -4,
            (LineType.NUMBER, LineType.NUMBER): -3,
            (LineType.ROLE, LineType.NUMBER): -2,
            (LineType.NUMBER, LineType.ROLE): -2,
        }

        return transitions.get(
            (previous, current),
            0,
       )
    
    def save_debug_report(
        self,
        page_number: int,
        analysis: dict,
    ) -> None:

        debug_dir = (
            Path(__file__).resolve().parents[2]
            / "storage"
            / "debug"
        )

        debug_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        output = debug_dir / f"reading_order_page_{page_number}.txt"

        with open(output, "w", encoding="utf-8") as f:

            f.write(f"Page: {page_number}\n")
            f.write(f"Sequence Score: {analysis['sequence_score']}\n")
            f.write(f"Role Runs: {analysis['role_runs']}\n")
            f.write("\n")

            for item in analysis["classified"]:
                f.write(
                    f"{item.line_type.name:<18}{item.text}\n"
                )