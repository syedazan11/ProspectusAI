from copy import deepcopy
from pathlib import Path
from typing import Any

from src.processing.table_extractor import TableExtractor
from src.processing.table_layout_analyzer import (
    TableLayoutAnalyzer,
)
from src.processing.table_parser import TableParser
from src.schemas.table import ExtractedTable
from src.processing.table_strategy_selector import (
    TableStrategySelector,
)
from src.extraction.vision_table_extractor import (
    VisionTableExtractor,
)
from src.extraction.table_block_normalizer import (
    TableBlockNormalizer,
)
from src.extraction.table_block_merger import (
    TableBlockMerger,
)
from src.extraction.table_validator import (
    TableValidator,
)
from src.extraction.table_recovery_planner import (
    TableRecoveryPlanner,
)


class TablePipeline:
    """
    Coordinates the complete table-processing pipeline.

    Flow:
    table image
        -> layout analysis
        -> strategy selection
        -> vision extraction
        -> normalization
        -> block merging
        -> validation
        -> targeted recovery
        -> safe recovery application
        -> final validation
        -> structured table
    """

    def __init__(self):
        self.layout_analyzer = TableLayoutAnalyzer()
        self.table_extractor = TableExtractor()
        self.table_parser = TableParser()
        self.strategy_selector = TableStrategySelector()
        self.vision_extractor = VisionTableExtractor()

        self.block_normalizer = TableBlockNormalizer()
        self.block_merger = TableBlockMerger()
        self.validator = TableValidator()
        self.recovery_planner = TableRecoveryPlanner()

    def analyze(
        self,
        image_path: Path,
    ) -> dict[str, Any]:

        return self.layout_analyzer.analyze(
            image_path=image_path,
        )

    def choose_strategy(
        self,
        layout: dict[str, Any],
    ) -> str:

        return self.strategy_selector.select(
            layout=layout,
        )

    def prepare_extraction(
        self,
        image_path: Path,
        page_number: int,
        layout: dict[str, Any],
        strategy: str,
    ) -> dict[str, Any]:

        if strategy == "adaptive_blocks":
            return self._process_adaptive_table(
                image_path=image_path,
                page_number=page_number,
                layout=layout,
            )

        if strategy == "single":
            return self.vision_extractor.extract_single(
                image_path=image_path,
                page_number=page_number,
            )

        raise ValueError(
            f"Unsupported extraction strategy: {strategy}"
        )

    def _process_adaptive_table(
        self,
        image_path: Path,
        page_number: int,
        layout: dict[str, Any],
    ) -> dict[str, Any]:

        extraction_result = (
            self.vision_extractor.extract_adaptive(
                image_path=image_path,
                page_number=page_number,
                layout=layout,
            )
        )

        source_blocks = extraction_result.get(
            "blocks",
            [],
        )

        normalized_blocks = (
            self.block_normalizer.normalize(
                source_blocks
            )
        )

        merged_table = self.block_merger.merge(
            normalized_blocks
        )

        initial_validation = self.validator.validate(
            merged_table
        )

        final_table = merged_table
        final_validation = initial_validation

        recovery_plan = (
            self.recovery_planner.create_plan(
                table=merged_table,
                validation=initial_validation,
                blocks=normalized_blocks,
            )
        )

        recovery_attempted = False
        recovery_accepted = False
        recovery_error = None

        if recovery_plan.get(
            "requires_recovery",
            False,
        ):
            recovery_attempted = True

            try:
                recovery_results = (
                    self.vision_extractor.recover_rows(
                        recovery_blocks=recovery_plan.get(
                            "recovery_blocks",
                            [],
                        ),
                        source_blocks=source_blocks,
                        recovery_rows=recovery_plan.get(
                            "recovery_rows",
                            [],
                        ),
                    )
                )

                candidate_table = deepcopy(
                    merged_table
                )

                candidate_table = (
                    self.recovery_planner.apply_recovery(
                        table=candidate_table,
                        recovery_results=recovery_results,
                        recovery_plan=recovery_plan,
                    )
                )

                candidate_validation = (
                    self.validator.validate(
                        candidate_table
                    )
                )

                if self._is_validation_better(
                    candidate=candidate_validation,
                    current=initial_validation,
                ):
                    final_table = candidate_table
                    final_validation = (
                        candidate_validation
                    )
                    recovery_accepted = True

            except (
                ValueError,
                RuntimeError,
            ) as error:
                recovery_error = str(error)

        final_table.setdefault(
            "metadata",
            {},
        )

        final_table["metadata"].update(
            {
                "page_number": page_number,
                "image_path": str(image_path),
                "extraction_strategy": (
                    "adaptive_blocks"
                ),
                "initial_validation": (
                    initial_validation
                ),
                "final_validation": (
                    final_validation
                ),
                "recovery_attempted": (
                    recovery_attempted
                ),
                "recovery_accepted": (
                    recovery_accepted
                ),
                "recovery_error": recovery_error,
            }
        )

        return final_table

    def _is_validation_better(
        self,
        candidate: dict[str, Any],
        current: dict[str, Any],
    ) -> bool:

        candidate_invalid = candidate.get(
            "invalid_total_count",
            0,
        )

        current_invalid = current.get(
            "invalid_total_count",
            0,
        )

        candidate_review = candidate.get(
            "needs_review_count",
            0,
        )

        current_review = current.get(
            "needs_review_count",
            0,
        )

        candidate_score = (
            candidate_invalid * 10
            + candidate_review
        )

        current_score = (
            current_invalid * 10
            + current_review
        )

        return candidate_score < current_score

    def process_extracted_data(
        self,
        table_data: dict[str, Any],
        page_number: int,
    ) -> tuple[
        ExtractedTable,
        list[dict[str, Any]],
    ]:

        extracted_table = self.table_extractor.extract(
            table_data=table_data,
            page_number=page_number,
        )

        chunks = []

        for row in extracted_table.rows:

            chunk = self.table_parser.build_row_chunk(
                table_title=(
                    extracted_table.table_title
                ),
                row=row,
                page_number=(
                    extracted_table.page_number
                ),
            )

            chunks.append(chunk)

        return extracted_table, chunks