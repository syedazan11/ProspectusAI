from dataclasses import dataclass, field

from .stream_builder import ReadingStream
import re

@dataclass(slots=True)
class ValidationIssue:

    page: int

    message: str


@dataclass(slots=True)
class ValidationResult:

    issues: list[ValidationIssue] = field(
        default_factory=list,
    )

    @property
    def valid(self) -> bool:
        return len(self.issues) == 0


class StreamValidator:

    def validate(
        self,
        stream: ReadingStream,
    ) -> ValidationResult:

        result = ValidationResult()

        seen_headings: dict[str, int] = {}

        for node in stream.nodes:

            text = node.line.text.strip()

            # Only consider numbered subsection headings
            if not re.match(r"^\d+(?:\.\d+)+\s+", text):
                continue

            if text in seen_headings:

                result.issues.append(
                    ValidationIssue(
                        page=node.page,
                        message=f"Duplicate subsection heading: {text}",
                    )
                )

            else:
                seen_headings[text] = node.page

        return result