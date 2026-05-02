from app.ingestion.ncert_manifest_builder import (
    BookSpec,
    extract_chapter_title_from_pdf,
    parse_book_specs,
    parse_class_subjects,
    select_canonical_book_specs,
)
from app.ingestion.ncert_http import extract_chapter_title_from_text


SAMPLE_TEXTBOOK_PAGE = """
else if (document.test.tclass.value==12)
{
    document.test.tsubject.options[1].text="Mathematics";
    document.test.tsubject.options[2].text="Computer Science";
}
if((document.test.tclass.value==12) && (document.test.tsubject.options[sind].text=="Computer Science"))
{
    document.test.tbook.options[1].text="Computer Science";
    document.test.tbook.options[1].value="textbook.php?lecs1=0-13";
}
"""


SAMPLE_PDF_TEXT_WRAPPED_TITLE = """
In this Chapter
Introduction
Chapter
1 Exception Handling
in Python
Chapter 1.indd   1 18-Jun-21   2:27:38 PM
"""


SAMPLE_PDF_TEXT_TITLE_BEFORE_NUMBER = """
Some chapter heading
Fallback title line
1
Chapter 1.indd   1 10/06/2024   11:09:02
"""


def test_parse_class_subjects_extracts_subject_names():
    result = parse_class_subjects(SAMPLE_TEXTBOOK_PAGE)
    assert result[12] == ["Mathematics", "Computer Science"]


def test_parse_book_specs_extracts_book_code_and_count():
    result = parse_book_specs(SAMPLE_TEXTBOOK_PAGE)
    assert len(result) == 1
    spec = result[0]
    assert spec.class_level == 12
    assert spec.subject == "Computer Science"
    assert spec.title == "Computer Science"
    assert spec.ncert_code == "lecs1"
    assert spec.chapter_count == 13


def test_extract_chapter_title_from_pdf_handles_wrapped_title(monkeypatch):
    from app.ingestion import ncert_http

    def fake_extract_pdf_text(_pdf_bytes):
        return SAMPLE_PDF_TEXT_WRAPPED_TITLE, 18, [SAMPLE_PDF_TEXT_WRAPPED_TITLE]

    monkeypatch.setattr(ncert_http, "extract_pdf_text", fake_extract_pdf_text)
    assert extract_chapter_title_from_pdf(b"%PDF-1.4 fake", 1) == "Exception Handling in Python"


def test_extract_chapter_title_from_pdf_handles_title_before_number(monkeypatch):
    from app.ingestion import ncert_http

    def fake_extract_pdf_text(_pdf_bytes):
        return SAMPLE_PDF_TEXT_TITLE_BEFORE_NUMBER, 18, [SAMPLE_PDF_TEXT_TITLE_BEFORE_NUMBER]

    monkeypatch.setattr(ncert_http, "extract_pdf_text", fake_extract_pdf_text)
    assert extract_chapter_title_from_pdf(b"%PDF-1.4 fake", 1) == "Fallback title line"


def test_extract_chapter_title_from_text_handles_title_with_number_and_chapter():
    text = """
The Wonderful World of Science1Chapter
As human beings, we have always been curious about our surroundings.
Chapter 1.indd   1 10/06/2024   11:09:02
"""

    assert extract_chapter_title_from_text(text, 1) == "The Wonderful World of Science"


def test_extract_chapter_title_from_text_handles_multiline_title_before_marker():
    text = """
Methods of Separation
in Everyday Life9
Chapter
Some body text starts here.
Chapter 9.indd   163 10/4/2024   3:10:10 PM
"""

    assert extract_chapter_title_from_text(text, 9) == "Methods of Separation in Everyday Life"


def test_extract_chapter_title_from_text_handles_title_after_chapter_marker():
    text = """
4
Chapter
Reshma lives in a coastal town.
Exploring Magnets
More paragraph text.
Chapter 4.indd   61 10/4/2024   3:16:10 PM
"""

    assert extract_chapter_title_from_text(text, 4) == "Exploring Magnets"


def test_select_canonical_book_specs_prefers_latest_plain_title():
    specs = [
        BookSpec(class_level=6, subject="Science", title="Curiosity", ncert_code="fecu1", chapter_count=12),
        BookSpec(class_level=6, subject="Science", title="Curiosity (Malayalam)", ncert_code="fmlcu1", chapter_count=12),
        BookSpec(class_level=6, subject="Science", title="Tajassus", ncert_code="fucu1", chapter_count=12),
    ]

    result = select_canonical_book_specs(specs)

    assert [spec.ncert_code for spec in result] == ["fecu1"]


def test_select_canonical_book_specs_keeps_part_books():
    specs = [
        BookSpec(
            class_level=12,
            subject="Home Science",
            title="Human Ecology and Family Sciences Part I",
            ncert_code="lhef1",
            chapter_count=8,
        ),
        BookSpec(
            class_level=12,
            subject="Home Science",
            title="Human Ecology and Family Sciences Part II",
            ncert_code="lhef2",
            chapter_count=7,
        ),
        BookSpec(
            class_level=12,
            subject="Home Science",
            title="Human Ecology and Family Sciences Part I (Hindi)",
            ncert_code="hhfs1",
            chapter_count=8,
        ),
    ]

    result = select_canonical_book_specs(specs)

    assert [spec.ncert_code for spec in result] == ["lhef1", "lhef2"]
