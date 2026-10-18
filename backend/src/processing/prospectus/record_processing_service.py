import json
from pathlib import Path
from src.processing.prospectus.fee_record_extractor import (
    FeeRecordExtractor,
)
from src.processing.prospectus.person_extractor import (
    PersonExtractor,
)
# from src.processing.prospectus.contact_extractor import (
#     ContactExtractor,
# )
# from src.processing.prospectus.academic_extractor import (
#     AcademicExtractor,
# )
# from src.processing.prospectus.admission_extractor import (
#     AdmissionExtractor,
# )
# from src.processing.prospectus.student_life_extractor import (
#     StudentLifeExtractor,
# )
# from src.processing.prospectus.governance_extractor import (
#     GovernanceExtractor,
# )
# from src.processing.prospectus.research_extractor import (
#     ResearchExtractor,
# )
from src.processing.prospectus.admission_category_extractor import (
    AdmissionCategoryExtractor,
)

class RecordProcessingService:
    """
    Runs all structured record extractors.
    """

    # def __init__(self) -> None:
    def __init__(
        self,
        layout_path: Path | None = None,
    ) -> None:
        self.layout_path = layout_path

        self.fee_extractor = (
            FeeRecordExtractor()
        )
        self.person_extractor = (
            PersonExtractor()
        )
        # self.contact_extractor = (
        #     ContactExtractor()
        # )
        # self.academic_extractor = (
        #     AcademicExtractor()
        # )
        # self.admission_extractor = (
        #     AdmissionExtractor()
        # )
        # self.student_life_extractor = (
        #     StudentLifeExtractor()
        # )
        # self.governance_extractor = (
        #     GovernanceExtractor()
        # )
        # self.research_extractor = (
        #     ResearchExtractor()
        #)
        self.admission_category_extractor = (
            AdmissionCategoryExtractor()
        )

    # def _load_layout_document(self) -> dict:

    #     layout_path = (
    #         Path(__file__).resolve().parents[4]
    #         / "storage"
    #         / "experiments"
    #         / "layout_reconstruction.json"
    #     )

    #     with open(layout_path, "r", encoding="utf-8") as f:
    #         return json.load(f)
    def _load_layout_document(self) -> dict:

        if self.layout_path is None:
            self.layout_path = (
                Path(__file__).resolve().parents[4]
                / "storage"
                / "experiments"
                / "layout_reconstruction.json"
            )

        with open(self.layout_path, "r", encoding="utf-8") as f:
            return json.load(f)
    

    def process(
        self,
        *,
        cleaned_document: dict,
        detected_sections: list,
    ) -> dict:

        layout_document = self._load_layout_document()

        fee_pages = []
        # curriculum_pages = []
        # admission_pages = []
        # # admission_category_pages = []
        # student_pages = []
        # governance_pages = []
        # research_pages = []

        start = None
        end = None

        for section in detected_sections:

            if section.section_type in (
                "scholarships",
                "student_support",
                "student_life",
            ):

                pages = [
                    page
                    for page in cleaned_document["pages"]
                    if (
                        section.start_page
                        <= page["page_number"]
                        <= section.end_page
                    )
                ]

                # student_pages.extend(pages)

            if section.section_type in (
                "regular_category_descriptions",
                "self_finance_category_descriptions",
            ):

                pages = [
                    page
                    for page in cleaned_document["pages"]
                    if (
                        section.start_page
                        <= page["page_number"]
                        <= section.end_page
                    )
                ]

        

                # print(
                #     f"[RECORD SERVICE] "
                #     f"{section.section_type}: "
                #     f"{section.start_page}-{section.end_page} "
                #     f"({len(pages)} pages)"
                # )
            

            # if section.section_type in (
            #     "eligibility",
            #     "admissions",
            # ):

                # pages = [
                #     page
                #     for page in cleaned_document["pages"]
                #     if (
                #         section.start_page
                #         <= page["page_number"]
                #         <= section.end_page
                #     )
                # ]

                # admission_pages.extend(
                #     pages
                # )

                # print(
                #     f"[RECORD SERVICE] "
                #     f"{section.section_type}: "
                #     f"{section.start_page}-{section.end_page} "
                #     f"({len(pages)} pages)"
                # )

            # if section.section_type == "curriculum":

            #     curriculum_pages = [
            #         page
            #         for page in cleaned_document["pages"]
            #         if (
            #             section.start_page
            #             <= page["page_number"]
            #             <= section.end_page
            #         )
            #     ]

            #     print(
            #         f"[RECORD SERVICE] Curriculum pages: "
            #         f"{section.start_page}-{section.end_page} "
            #         f"({len(curriculum_pages)} pages)"
            #     )

            if section.section_type == "finance":
                start = section.start_page
                end = section.end_page

                fee_pages = [
                    page
                    for page in cleaned_document["pages"]
                    if (
                        start
                        <= page["page_number"]
                        <= end
                    )
                ]


        # if start is not None:

            # print(
            #     f"[RecordProcessingService] "
            #     f"fee_structure -> pages "
            #     f"{start}-{end} "
            #     f"({len(fee_pages)} pages)"
            # )
        
            # print(
            #     f"[RECORD SERVICE] Fee pages: {start}-{end} ({len(fee_pages)} pages)"
            # )

        fees = self.fee_extractor.extract(
            layout_document=cleaned_document, #layout_document,
            pages=fee_pages,
        )

        # print(
        #     f"FEE RECORDS: {len(fees)}"
        # )

        # for record in fees:
        #     print(record)

        faculty_pages = set()

        for section in detected_sections:

            if section.section_type == "faculty_roles":

                # for page in layout_document["pages"]:
                for page in layout_document:

                    if (
                        section.start_page
                        <= page["page_number"]
                        <= section.end_page
                    ):
                        faculty_pages.add(
                            page["page_number"]
                        )
        
        people = self.person_extractor.extract(
            layout_document,
            faculty_pages=faculty_pages,
        )

        # print(
        #     f"PERSON RECORDS: {len(people)}"
        # )

        # for record in people:
        #     print(record)
        
        # contacts = self.contact_extractor.extract(
        #     cleaned_document["pages"]
        # )
        
        # print(f"CONTACT RECORDS: {len(contacts)}")

        # # for record in contacts:
        # #     print(record)

        # admissions = self.admission_extractor.extract(
        #     admission_pages
        # )

        # print(
        #     f"ADMISSION RECORDS: {len(admissions)}"
        # )

        # for record in admissions:
        #     print(record)

        admission_category_pages = set()

        for section in detected_sections:

            if section.section_type in (
                "regular_category_descriptions",
                "self_finance_category_descriptions",
            ):

                admission_category_pages.update(
                    range(
                        section.start_page,
                        section.end_page + 1,
                    )
                )

        admission_categories = (
            self.admission_category_extractor.extract(
                layout_document=layout_document,
                pages=admission_category_pages,
            )
        )
        # print("\n========== ADMISSION CATEGORY PAGES ==========")
        # print(sorted(admission_category_pages))
        # print(f"TOTAL PAGES: {len(admission_category_pages)}")

        # print("\n===== SAMPLE RECORDS =====")

        # for record in admission_categories:
        #     print(record)

        # print(
        #     f"ADMISSION CATEGORY RECORDS: "
        #     f"{len(admission_categories)}"
        # )

        # student_life = (
        #     self.student_life_extractor.extract(
        #         student_pages
        #     )
        # )

        # print(
        #     f"STUDENT LIFE RECORDS: "
        #     f"{len(student_life)}"
        # )

        # for record in student_life:
        #     print(record)

        # governance = (
        #     self.governance_extractor.extract(
        #         cleaned_document["pages"]
        #     )
        # )

        # print(
        #     f"GOVERNANCE RECORDS: "
        #     f"{len(governance)}"
        # )

        # for record in governance:
        #     print(record)

        # research = (
        #     self.research_extractor.extract(
        #         cleaned_document["pages"]
        #     )
        # )

        # print(
        #     f"RESEARCH RECORDS: "
        #     f"{len(research)}"
        # )

        # for record in research:
        #     print(record)


        # academics = self.academic_extractor.extract(
        #     curriculum_pages
        # )

        # print(
        #     f"ACADEMIC RECORDS: {len(academics)}"
        # )

        # for record in academics:
        #     print(record)
        

        return {
            "fees": fees,
            "people": people,
            # "admissions": admissions,
            # "academics": academics,
            # "student_life": student_life,
            # "governance": governance,
            # "research": research,
            # "contacts": contacts,
            "admission_categories": admission_categories,
        }