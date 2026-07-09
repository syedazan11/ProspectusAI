from src.processing.prospectus.text_normalizer import (
    ProspectusTextNormalizer,
)


def test_removes_repeated_headers():
    normalizer = ProspectusTextNormalizer()

    lines = normalizer.normalize_page(
        "NED UNIVERSITY\n"
        "UNDERGRADUATE\n"
        "PROSPECTUS 2025\n"
        "8.1 FEE AND CHARGES\n"
    )

    assert lines == [
        "8.1 FEE AND CHARGES"
    ]


def test_preserves_real_content():
    normalizer = ProspectusTextNormalizer()

    lines = normalizer.normalize_page(
        "Admission Fee to be paid once "
        "at the time of Admission"
    )

    assert lines == [
        "Admission Fee to be paid once "
        "at the time of Admission"
    ]


def test_detects_numbered_heading():
    normalizer = ProspectusTextNormalizer()

    assert normalizer.is_heading(
        "8.1 FEE AND CHARGES (NON-REFUNDABLE)"
    )


def test_detects_uppercase_heading():
    normalizer = ProspectusTextNormalizer()

    assert normalizer.is_heading(
        "ADMISSION POLICY"
    )


def test_long_uppercase_text_is_not_heading():
    normalizer = ProspectusTextNormalizer()

    text = (
        "THIS IS A VERY LONG OCR PARAGRAPH "
        * 10
    )

    assert not normalizer.is_heading(text)


def test_detects_course_table_signal():
    normalizer = ProspectusTextNormalizer()

    assert normalizer.is_table_signal(
        "Fall Semester"
    )


def test_course_table_labels_are_not_headings():
    normalizer = ProspectusTextNormalizer()

    false_headings = [
        "Fall Semester",
        "Spring Semester",
        "Course",
        "Course Title",
        "Credit Hours",
    ]

    for text in false_headings:
        assert not normalizer.is_heading(text)


def test_real_ocr_fragments_are_not_headings():
    normalizer = ProspectusTextNormalizer()

    false_headings = [
        "NED",
        "UNIVERSITY OF",
        "COMPUTER SCI",
        "DEPARTNEN",
        "INFORMATION TE",
        "V",
    ]

    for text in false_headings:
        assert not normalizer.is_heading(text)


def test_real_numbered_sections_are_headings():
    normalizer = ProspectusTextNormalizer()

    headings = [
        "8.1 FEE AND CHARGES (NON-REFUNDABLE)",
        "10.11.1 Objectives",
        "2.2.24 Department of Physics",
    ]

    for text in headings:
        assert normalizer.is_heading(text)


def test_removes_real_prospectus_footer_noise():
    normalizer = ProspectusTextNormalizer()

    lines = normalizer.normalize_page(
        "Admission information\n"
        "www.neduet.edu.pk\n"
        "+NEDUET Official\n"
        "83\n"
        "Ã‚Â©+NEDUET Official"
    )

    assert lines == [
        "Admission information"
    ]
