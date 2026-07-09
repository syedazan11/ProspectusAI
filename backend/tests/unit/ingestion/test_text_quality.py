from src.ingestion.extraction.text_quality import (
    TextQualityAnalyzer,
)


def test_good_native_text_is_usable():
    analyzer = TextQualityAnalyzer()

    text = (
        "Admission to undergraduate programmes "
        "at NED University is based on eligibility "
        "requirements stated in the prospectus."
    )

    result = analyzer.analyze(text)

    assert result.is_usable is True
    assert result.character_count >= 40
    assert result.word_count >= 8
    assert result.reasons == []


def test_empty_text_requires_ocr():
    analyzer = TextQualityAnalyzer()

    result = analyzer.analyze("")

    assert result.is_usable is False
    assert "too_few_characters" in result.reasons
    assert "too_few_words" in result.reasons


def test_tiny_text_requires_ocr():
    analyzer = TextQualityAnalyzer()

    result = analyzer.analyze("NED")

    assert result.is_usable is False
    assert "too_few_characters" in result.reasons


def test_symbol_noise_requires_ocr():
    analyzer = TextQualityAnalyzer()

    text = (
        "@@@ ### $$$ %%% &&& *** !!! "
        "??? /// ||| ~~~ ^^^"
    )

    result = analyzer.analyze(text)

    assert result.is_usable is False
    assert "low_alphanumeric_ratio" in result.reasons


def test_corrupted_replacement_characters_fail():
    analyzer = TextQualityAnalyzer()

    text = (
        "This page contains enough ordinary words "
        "but has corrupted extraction characters "
        "......"
    ).replace(".", "\ufffd", 6)

    result = analyzer.analyze(text)

    assert result.is_usable is False
    assert (
        "too_many_replacement_characters"
        in result.reasons
    )
