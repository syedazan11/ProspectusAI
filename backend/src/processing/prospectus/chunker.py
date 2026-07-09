from src.processing.prospectus.chunk_models import (
    ProspectusChunk,
)
from src.processing.prospectus.text_normalizer import (
    ProspectusTextNormalizer,
)


class ProspectusChunker:
    TARGET_SIZE = 1200
    MAX_SIZE = 2000
    MIN_SIZE = 120

    def __init__(self) -> None:
        self.normalizer = ProspectusTextNormalizer()

    def chunk_page(
        self,
        page_number: int,
        text: str,
    ) -> list[ProspectusChunk]:
        lines = self.normalizer.normalize_page(text)

        chunks: list[ProspectusChunk] = []
        buffer: list[str] = []
        current_heading: str | None = None

        def flush() -> None:
            nonlocal buffer

            chunk_text = "\n".join(buffer).strip()

            if chunk_text:
                chunks.append(
                    ProspectusChunk(
                        chunk_id="",
                        page_number=page_number,
                        text=chunk_text,
                        section_heading=current_heading,
                        character_count=len(chunk_text),
                    )
                )

            buffer = []

        for line in lines:
            if self.normalizer.is_heading(line):
                flush()
                current_heading = line
                buffer.append(line)
                continue

            candidate = "\n".join(
                buffer + [line]
            ).strip()

            if (
                buffer
                and len(candidate) > self.TARGET_SIZE
            ):
                flush()

            buffer.append(line)

            if len("\n".join(buffer)) >= self.MAX_SIZE:
                flush()

        flush()

        return self._merge_tiny_chunks(chunks)

    def chunk_document(
        self,
        pages: list[dict],
    ) -> list[ProspectusChunk]:
        chunks: list[ProspectusChunk] = []

        for page in pages:
            chunks.extend(
                self.chunk_page(
                    page_number=page["page_number"],
                    text=page["text"],
                )
            )

        for index, chunk in enumerate(
            chunks,
            start=1,
        ):
            chunk.chunk_id = f"ug2025-{index:04d}"

        return chunks

    def _merge_tiny_chunks(
        self,
        chunks: list[ProspectusChunk],
    ) -> list[ProspectusChunk]:
        if len(chunks) < 2:
            return [
                chunk
                for chunk in chunks
                if chunk.character_count >= self.MIN_SIZE
            ]

        result: list[ProspectusChunk] = []
        index = 0

        while index < len(chunks):
            chunk = chunks[index]

            if chunk.character_count >= self.MIN_SIZE:
                result.append(chunk)
                index += 1
                continue

            if result:
                previous = result[-1]

                combined_size = (
                    previous.character_count
                    + 1
                    + chunk.character_count
                )

                if combined_size <= self.MAX_SIZE:
                    previous.text = (
                        previous.text
                        + "\n"
                        + chunk.text
                    )
                    previous.character_count = len(
                        previous.text
                    )
                    index += 1
                    continue

            if index + 1 < len(chunks):
                next_chunk = chunks[index + 1]

                combined_size = (
                    chunk.character_count
                    + 1
                    + next_chunk.character_count
                )

                if combined_size <= self.MAX_SIZE:
                    next_chunk.text = (
                        chunk.text
                        + "\n"
                        + next_chunk.text
                    )
                    next_chunk.character_count = len(
                        next_chunk.text
                    )

                    if (
                        chunk.section_heading
                        and not next_chunk.section_heading
                    ):
                        next_chunk.section_heading = (
                            chunk.section_heading
                        )

                    result.append(next_chunk)
                    index += 2
                    continue

            result.append(chunk)
            index += 1

        return [
            chunk
            for chunk in result
            if chunk.character_count >= self.MIN_SIZE
        ]
