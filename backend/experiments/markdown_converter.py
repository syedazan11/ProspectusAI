from __future__ import annotations

import json
import re
from pathlib import Path


class MarkdownConverter:

    def convert(
        self,
        layout_document: dict,
    ) -> str:

        markdown = []

        for page in layout_document:

            markdown.append(
                f"\n<!-- PAGE {page['page_number']} -->\n"
            )

            text = page["reconstructed_text"]

            markdown.extend(
                self._convert_page(text)
            )

        return "\n".join(markdown)

    def _convert_page(
        self,
        text: str,
    ) -> list[str]:

        output = []

        lines = self._merge_headings(
            text.splitlines()
        )

        for line in lines:

            line = line.strip()

            if self._skip_line(line):
                continue

            if self._is_false_heading(line):
                level = 0
            else:
                level = self._classify(line)

            if level == 1:
                output.append(f"# {line}")

            elif level == 2:
                output.append(f"## {line}")

            elif level == 3:
                output.append(f"### {line}")

            elif level == 4:
                output.append(f"#### {line}")

            else:
                output.append(line)

        return output

    def _skip_line(
        self,
        line: str,
    ) -> bool:

        line = line.strip()

        if not line:
            return True

    #
    # Website
    #

        if "www.neduet.edu.pk" in line.lower():
            return True

    #
    # Common page decorations
    #

        SKIP = {

            "UNDERGRADUATE",
            "NED UNIVERSITY",
            "OF ENGINEERING & TECHNOLOGY",
            "PROSPECTUS ",
            "KARACHI",
            "NED UNIVERSITY",
            "NEDUET",
            "KARACI",
            "NEDUETOfficial",
            "YouthLaptopScheme",
            "LEVELUP",
        }

        for text in SKIP:
            if text.lower() in line.lower():
                return True

        if re.fullmatch(
            r"PROSPECTUS\s+\d{4}",
            line,
            re.IGNORECASE,
        ):
            return True

    #
    # Roman numeral page numbers
    #

        if re.fullmatch(
            r"[ivxlcdm]+",
            line.lower(),
        ):
            return True

    #
    # Pure page numbers
    #

        if re.fullmatch(
            r"\d+",
            line,
        ):
            return True

    #
    # Header/footer patterns
    #

        if re.match(
            r"^\d+\s+\d+\s+www\.",
            line.lower(),
        ):
            return True

    #
    # BCIT, NEDUET; MCIT, NEDUET
    #

        if (
            line.isupper()
            and line.count(",") >= 2
        ):
            return True

        return False

    def _merge_headings(
        self,
        lines: list[str],
    ) -> list[str]:

        merged = []

        i = 0

        while i < len(lines):

            line = lines[i].strip()

            if not line:
                i += 1
                continue

            #
            # Numbered list items
            #
            # 1. Muhammad...
            # 2. Increasing...
            # 3 network racks...


            if re.match(r"^\d+\.", line):

                rest = re.sub(r"^\d+\.\s*", "", line)

                # Person names
                if re.match(r"^(Mr|Mrs|Ms|Miss|Dr|Prof|Engr)\.?\s", rest):
                    merged.append(line)
                    i += 1
                    continue

    # List sentence
                if len(rest.split()) > 4:
                    merged.append(line)
                    i += 1
                    continue

    #
    # Starts with number but not section numbering
    #

            if re.match(r"^\d+\s", line):
                    merged.append(line)
                    i += 1
                    continue

        #
        # Numbered heading
        #

            if re.match(
            
                r"^(?:\d+(?:\.\d+)*(?:\([^)]+\))?|(?:R|SF)-\d+(?:\([a-z]\))?)",
                line,
                re.IGNORECASE,
            ):

                heading = line

                j = i + 1

                while j < len(lines):

                    nxt = lines[j].strip()

                    if not nxt:
                        break

                #
                # Stop if another numbered heading
                #

                    if re.match(
                        r"^\d+(?:\.\d+)*(?:\([^)]+\))?",
                        nxt,
                    ):
                        break

                #
                # Stop if category heading
                #

                    if re.match(
                        r"^(R|SF)-\d+",
                        nxt,
                    ):
                        break

                #
                # Stop if faculty label
                #

                    if nxt in {
                        "Chairperson",
                        "Co-Chairperson",
                        "Professor",
                        "Professors",
                        "Associate Professor",
                        "Associate Professors",
                        "Assistant Professor",
                        "Assistant Professors",
                        "Lecturer",
                        "Lecturers",
                    }:
                        break

                #
                # Don't absorb tables
                #

                    if re.match(
                        r"^[A-Z+]+\s+\d",
                        nxt,
                    ):
                        break

                #
                # Don't absorb list items
                #

                    if re.match(
                        r"^[ivx]+\)",
                        nxt,
                        re.I,
                    ):
                        break

                    if re.match(
                        r"^\d+\.",
                        nxt,
                    ):
                        break

                    first_word = nxt.split()[0] if nxt.split() else ""

                    first_word = first_word.lower()

                    PARAGRAPH_STARTS = {
                        "the",
                        "this",
                        "these",
                        "candidates",
                        "students",
                        "applicant",
                        "applicants",
                        "university",
                        "admission",
                        "all",
                        "if",
                        "after",
                        "before",
                        "during",
                        "every",
                        "each",
                        "such",
                        "any",
                        "no",
                        "for",
                        "in",
                        "on",
                        "at",
                        "by",
                        "under",
                        "subject",
                        "according",
                        "as",
                        "with",
                        "without",
                        "from",
                        "to",
                        "through",
                        "within",
                        "among",
                        "between",
                        "while",
                        "whereas",
                        "where",
                        "when",
                        "which",
                        "who",
                        "whom",
                        "whose",
                        "that",
                        "whether",
                        "because",
                        "although",
                        "though",
                        "since",
                        "unless",
                        "until",
                        "provided",
                        "given",
                        "considering",
                        "regarding",
                        "concerning",
                        "following",
                        "pursuant",
                        "insofar",
                    }

                    if first_word in PARAGRAPH_STARTS:
                        break

                    heading += " " + nxt

                    j += 1

                merged.append(heading)

                i = j

                continue

            merged.append(line)

            i += 1

        return merged

    def _is_false_heading(
        self,
        line: str,
    ) -> bool:

    #
    # Degree lines
    #

        if re.match(
            r"^(B\.?E\.?|B\.?S\.?|B\.?Sc\.?|M\.?E\.?|M\.?S\.?|M\.?Sc\.?|MBA|M\.Phil|Ph\.?D)",
            line,
            re.I,
        ):
            return True

    #
    # Grade table rows
    #

        if re.match(
            r"^(A\+|A-|A|B\+|B-|B|C\+|C-|C|D\+|D|F|P|IP|X|I|W|WU)\b",
            line,
        ):
            return True

    #
    # Numeric table rows
    #

        if re.match(
            r"^[A-Za-z+]+\s+\d+\.\d+",
            line,
        ):
            return True

    #
    # Random OCR noise
    #

        letters = sum(c.isalpha() for c in line)

        if letters > 8:

            vowels = sum(
                c.lower() in "aeiou"
                for c in line
                if c.isalpha()
            )

            if vowels / letters < 0.15:
                return True

    #
    # Sentences with punctuation in middle
    #

        if any(ch in line for ch in ['"', "'", "?", ";"]):
            return True


        #
        # Looks like a table row
        #

        if re.search(r"\d+%", line):
            return True

        if re.search(r"\bRs\.?\b", line):
            return True

        if re.search(r"\bPKR\b", line, re.I):
            return True

        if re.search(r"\bmbps\b", line, re.I):
            return True

        if re.search(r"\bGbps\b", line, re.I):
            return True

        if re.search(r"\bTimeline\b", line):
            return True

        if re.match(r"^\d+\s+[a-z]", line, re.I):
            return True

        return False

    def _classify(
        self,
        line: str,
    ) -> int:

        line = line.strip()

        if not line:
            return 0

        tokens = line.split()

        numeric_tokens = sum(
    1
    for token in tokens
    if re.search(r"\d", token)
)

        if numeric_tokens >= 4:
            return 0

    # --------------------------------------------------
    # Numbered headings
    #
    # Examples:
    # 1 General Information
    # 2.2 Teaching Departments
    # 2.2.15 Department of Chemical Engineering
    # 5.1(ii) Transfer of Seats
    # 4.1.2 Candidates shall...
    # --------------------------------------------------

        numbered = re.match(
            r"^(?P<number>[1-9]\d?(?:\.\d+)+(?:\([ivxlcdm]+\))?)\.?\s+(?P<title>.+)$",
            line,
            re.IGNORECASE,
        )

        if numbered:

            number = numbered.group("number")
            title = numbered.group("title").strip()

            depth = number.count(".")

        #
        # Very long numbered sentences ending with :
        # are section headings.
        #

            if line.endswith(":"):
                return 3

        #
        # 1
        #

            if depth == 0:
                return 1

        #
        # 2.2
        #

            if depth == 1:
                return 2

        #
        # 2.2.15
        # 4.1.2
        # 5.1(ii)
        #

            return 3

        if re.match(
            r"^(B\.|M\.|Ph\.D|MBA|MS|BE|BS)",
            line,
            re.I,
        ):
            return 0

        DEPARTMENT_WORDS = (
            "Department of",
            "Dean of",
            "Directorate of",
            "Office of",
        )
        
        if line.startswith(DEPARTMENT_WORDS):
            return 3

    # --------------------------------------------------
    # Admission Categories
    #
    # R-1(a)
    # SF-2(b)
    # K-1(c)
    # --------------------------------------------------

        if re.match(
            r"^(R|SF)-\d+(?:\([a-z]\))?\b",
            line,
        ):
            return 3

    # --------------------------------------------------
    # Uppercase headings
    # --------------------------------------------------

        if (
            line.isupper()
            and 2 <= len(line.split()) <= 8
            and len(line) < 80
        ):
            return 1

    # --------------------------------------------------
    # Faculty labels
    # --------------------------------------------------

        LABELS = {

            "Chairperson",
            "Co-Chairperson",
            "Chairman",
            "Faculty Members",
            "Professors",
            "Professor",
            "Vice Chancellor",
            "Dean",
            "Pro Vice-Chancellor",
            "Associate Professors",
            "Associate Professor",
            "Assistant Professors",
            "Assistant Professor",
            "Adjunct Faculty",
            "Lecturers",
            "Lecturer",
            "IT Managers",
            "IT Manager",
            "Lab Engineers",
            "Lab Engineer",
            "Objectives",
            "Facilities",
            "Eligibility",
            "Duration",
            "Vision",
            "VISION",
            "Mission",
            "Laboratories",
            "Research Areas",
        }

        if line in LABELS:
            return 4

        return 0

    def _is_label(
        self,
        line: str,
    ) -> bool:

        words = line.split()

        if len(words) == 0:
            return False

        if len(words) > 5:
            return False

        if line.endswith("."):
            return False

        return all(
            word[:1].isupper()
            for word in words
        )


if __name__ == "__main__":

    input_file = (
        Path(__file__).resolve().parents[2]
        / "storage"
        / "experiments"
        / "layout_reconstruction.json"
    )

    with open(
        input_file,
        "r",
        encoding="utf-8",
    ) as f:

        layout = json.load(f)

    markdown = MarkdownConverter().convert(layout)

    output = (
        Path(__file__).resolve().parents[2]
        / "storage"
        / "experiments"
        / "document.md"
    )

    output.write_text(
        markdown,
        encoding="utf-8",
    )

    print(f"Saved -> {output}")
