from io import BytesIO

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from app.llm.schemas.worksheet import WorksheetOutput, WorksheetQuestionType


def render_worksheet_pdf(
    worksheet: WorksheetOutput,
    *,
    class_level: int,
    subject: str,
    chapter_title: str,
    include_answer_key: bool = True,
) -> bytes:
    """Render a worksheet into a printable A4 PDF.

    Includes a question section (no answers shown) and, if requested, an
    answer-key page at the end for the teacher.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=worksheet.title,
        author="School Tuter",
    )

    styles = _build_styles()
    story: list = []

    story.append(Paragraph(f"Class {class_level} &middot; {subject}", styles["meta"]))
    story.append(Paragraph(chapter_title, styles["meta"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(worksheet.title, styles["title"]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(
        Paragraph(
            f"Total marks: <b>{worksheet.total_marks}</b> &middot; "
            f"Questions: <b>{len(worksheet.questions)}</b>",
            styles["meta"],
        )
    )
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Instructions: " + worksheet.instructions, styles["instructions"]))
    story.append(Spacer(1, 0.5 * cm))

    for index, question in enumerate(worksheet.questions, start=1):
        story.append(
            KeepTogether(_render_question_block(index, question, styles))
        )
        story.append(Spacer(1, 0.4 * cm))

    if include_answer_key:
        story.append(PageBreak())
        story.append(Paragraph("Answer Key", styles["title"]))
        story.append(Paragraph(f"{worksheet.title}", styles["meta"]))
        story.append(Spacer(1, 0.4 * cm))
        for index, question in enumerate(worksheet.questions, start=1):
            story.append(KeepTogether(_render_answer_block(index, question, styles)))
            story.append(Spacer(1, 0.3 * cm))

    doc.build(story)
    return buffer.getvalue()


def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=base["Title"], fontSize=18, spaceAfter=6, alignment=TA_LEFT
        ),
        "meta": ParagraphStyle(
            "meta", parent=base["BodyText"], fontSize=10, textColor="#555555"
        ),
        "instructions": ParagraphStyle(
            "instructions", parent=base["BodyText"], fontSize=10, leading=14
        ),
        "question_number": ParagraphStyle(
            "question_number",
            parent=base["BodyText"],
            fontSize=11,
            leading=14,
            fontName="Helvetica-Bold",
        ),
        "question_body": ParagraphStyle(
            "question_body", parent=base["BodyText"], fontSize=11, leading=15
        ),
        "option": ParagraphStyle(
            "option",
            parent=base["BodyText"],
            fontSize=10,
            leading=13,
            leftIndent=1 * cm,
        ),
        "answer_label": ParagraphStyle(
            "answer_label",
            parent=base["BodyText"],
            fontSize=10,
            leading=13,
            textColor="#0b6623",
            fontName="Helvetica-Bold",
        ),
        "answer_body": ParagraphStyle(
            "answer_body", parent=base["BodyText"], fontSize=10, leading=13
        ),
    }


def _render_question_block(index: int, q, styles: dict[str, ParagraphStyle]) -> list:
    header_bits = [f"Q{index}.", q.question]
    marks = f"[{q.marks} mark{'s' if q.marks != 1 else ''}]"
    header = " ".join(header_bits) + f"  <font color='#888888'>{marks}</font>"
    block: list = [Paragraph(_escape(header), styles["question_body"])]

    if q.type in (WorksheetQuestionType.MCQ, WorksheetQuestionType.TRUE_FALSE) and q.options:
        letters = ["A", "B", "C", "D"]
        for letter, option in zip(letters, q.options, strict=False):
            block.append(Paragraph(f"({letter}) {_escape(option)}", styles["option"]))

    if q.type == WorksheetQuestionType.FILL_BLANK:
        pass
    elif q.type in (WorksheetQuestionType.SHORT_ANSWER, WorksheetQuestionType.LONG_ANSWER):
        space_cm = 2 if q.type == WorksheetQuestionType.SHORT_ANSWER else 4
        block.append(Spacer(1, space_cm * cm))

    return block


def _render_answer_block(index: int, q, styles: dict[str, ParagraphStyle]) -> list:
    block: list = [
        Paragraph(f"Q{index}. {_escape(q.question)}", styles["question_body"]),
        Paragraph(f"Answer: {_escape(q.answer)}", styles["answer_label"]),
    ]
    if q.explanation:
        block.append(Paragraph(_escape(q.explanation), styles["answer_body"]))
    tags: list[str] = [q.type.value, q.difficulty.value]
    if q.outcome_code:
        tags.append(q.outcome_code)
    block.append(
        Paragraph(
            f"<font color='#888888'>{' &middot; '.join(tags)}</font>",
            styles["answer_body"],
        )
    )
    return block


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
