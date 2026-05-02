import argparse
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings
from app.ingestion.ncert_http import (
    NCERT_TEXTBOOK_PAGE_URL,
    download_pdf,
    extract_chapter_title_from_pdf,
    fetch_text,
)
from app.ingestion.ncert_import import build_chapter_pdf_url


CLASS_HEADER_PATTERN = re.compile(r"else if\s*\(\s*document\.test\.tclass\.value==(\d+)\s*\)")
BOOK_HEADER_PATTERN = re.compile(
    r'if\s*\(\(document\.test\.tclass\.value==(\d+)\)\s*&&\s*\(document\.test\.tsubject\.options\[sind\]\.text=="([^"]+)"\)\)'
)
SUBJECT_TEXT_PATTERN = re.compile(r'^\s*document\.test\.tsubject\.options\[(\d+)\]\.text="([^"]*)"',
                                  re.MULTILINE)
BOOK_TEXT_PATTERN = re.compile(r'^\s*document\.test\.tbook\.options\[(\d+)\]\.text="([^"]*)";',
                               re.MULTILINE)
BOOK_VALUE_PATTERN = re.compile(
    r'^\s*document\.test\.tbook\.options\[(\d+)\]\.value="textbook\.php\?([A-Za-z0-9]+)=0-(\d+)"',
    re.MULTILINE,
)
PART_SUFFIX_PATTERN = re.compile(r"\bpart\s*(i{1,3}|iv|v|1|2|3|4|5)\b", re.IGNORECASE)
LANGUAGE_SUFFIX_PATTERN = re.compile(r"\s*\([^)]*\)\s*$")
URDU_SUFFIX_PATTERN = re.compile(r"\s*[-(]?\s*urdu\s*\)?\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class BookSpec:
    class_level: int
    subject: str
    title: str
    ncert_code: str
    chapter_count: int


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an NCERT manifest from the live textbook site.")
    parser.add_argument("--output", default="data/ncert_manifest.generated.json", help="Output manifest path.")
    parser.add_argument("--academic-year", default="2026-27", help="Academic year to record in the manifest.")
    parser.add_argument("--min-class", type=int, default=6, help="Minimum class level to include.")
    parser.add_argument("--max-class", type=int, default=12, help="Maximum class level to include.")
    parser.add_argument("--limit-books", type=int, default=None, help="Optional cap on books to process.")
    parser.add_argument(
        "--limit-chapters-per-book",
        type=int,
        default=None,
        help="Optional cap on chapters per book to process.",
    )
    parser.add_argument(
        "--skip-chapter-titles",
        action="store_true",
        help="Only build the manifest structure without downloading chapter PDFs.",
    )
    args = parser.parse_args()

    manifest = build_manifest(
        academic_year=args.academic_year,
        min_class=args.min_class,
        max_class=args.max_class,
        limit_books=args.limit_books,
        limit_chapters_per_book=args.limit_chapters_per_book,
        include_chapter_titles=not args.skip_chapter_titles,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps({"output": str(output_path), "classes": len(manifest["classes"])}, indent=2))


def build_manifest(
    *,
    academic_year: str,
    min_class: int = 6,
    max_class: int = 12,
    limit_books: int | None = None,
    limit_chapters_per_book: int | None = None,
    include_chapter_titles: bool = True,
) -> dict:
    page = fetch_text(NCERT_TEXTBOOK_PAGE_URL)
    class_subjects = parse_class_subjects(page)
    book_specs = parse_book_specs(page)
    book_specs = [
        spec
        for spec in book_specs
        if min_class <= spec.class_level <= max_class and spec.subject in class_subjects.get(spec.class_level, [])
    ]
    book_specs = select_canonical_book_specs(book_specs)

    if limit_books is not None:
        book_specs = book_specs[:limit_books]

    classes: list[dict] = []

    for class_level in range(min_class, max_class + 1):
        subjects = class_subjects.get(class_level, [])
        if not subjects:
            continue
        class_entry = {"level": class_level, "subjects": []}
        classes.append(class_entry)

    processed_books = 0
    for spec in book_specs:
        class_entry = next((item for item in classes if item["level"] == spec.class_level), None)
        if class_entry is None:
            continue
        subject_entries = class_entry["subjects"]
        subject_entry = next((item for item in subject_entries if item["name"] == spec.subject), None)
        if subject_entry is None:
            subject_entry = {"name": spec.subject, "language": "en", "books": []}
            subject_entries.append(subject_entry)

        book_entry = {
            "title": spec.title,
            "ncert_code": spec.ncert_code,
            "source_url": _build_book_source_url(spec.ncert_code, spec.chapter_count),
            "chapters": [],
        }
        chapter_limit = spec.chapter_count if limit_chapters_per_book is None else min(spec.chapter_count, limit_chapters_per_book)
        for chapter_number in range(1, chapter_limit + 1):
            pdf_url = build_chapter_pdf_url(
                base_url=get_settings().ncert_base_url,
                ncert_code=spec.ncert_code,
                chapter_number=chapter_number,
            )
            chapter_title = extract_chapter_title_from_pdf(download_pdf(pdf_url), chapter_number) if include_chapter_titles else None
            chapter_entry = {"number": chapter_number, "pdf_url": pdf_url}
            if chapter_title:
                chapter_entry["title"] = chapter_title
            book_entry["chapters"].append(chapter_entry)

        subject_entry["books"].append(book_entry)
        processed_books += 1

    return {
        "academic_year": academic_year,
        "is_current": True,
        "base_url": get_settings().ncert_base_url,
        "classes": classes,
        "meta": {
            "source_url": NCERT_TEXTBOOK_PAGE_URL,
            "books_processed": processed_books,
        },
    }


def parse_class_subjects(page: str) -> dict[int, list[str]]:
    class_subjects: dict[int, list[str]] = {}
    class_headers = list(CLASS_HEADER_PATTERN.finditer(page))
    for index, header in enumerate(class_headers):
        class_level = int(header.group(1))
        start = header.end()
        end = class_headers[index + 1].start() if index + 1 < len(class_headers) else page.find("function change1")
        if end == -1:
            end = len(page)
        body = page[start:end]
        subjects = []
        for _, text in sorted(_collect_text_assignments(body, SUBJECT_TEXT_PATTERN).items()):
            if text and not text.startswith("..Select"):
                subjects.append(html.unescape(text))
        class_subjects[class_level] = subjects
    return class_subjects


def parse_book_specs(page: str) -> list[BookSpec]:
    specs: list[BookSpec] = []
    headers = list(BOOK_HEADER_PATTERN.finditer(page))
    for index, header in enumerate(headers):
        class_level = int(header.group(1))
        subject = html.unescape(header.group(2))
        start = header.end()
        end = headers[index + 1].start() if index + 1 < len(headers) else len(page)
        body = page[start:end]
        text_assignments = _collect_text_assignments(body, BOOK_TEXT_PATTERN)
        value_assignments = _collect_value_assignments(body)
        for option_index, title in sorted(text_assignments.items()):
            value = value_assignments.get(option_index)
            if value is None:
                continue
            ncert_code, chapter_count = value
            if not title or title.startswith("..Select"):
                continue
            specs.append(
                BookSpec(
                    class_level=class_level,
                    subject=subject,
                    title=html.unescape(title),
                    ncert_code=ncert_code,
                    chapter_count=chapter_count,
                )
            )
    return specs


def select_canonical_book_specs(specs: list[BookSpec]) -> list[BookSpec]:
    canonical_specs: list[BookSpec] = []
    grouped: dict[tuple[int, str], list[BookSpec]] = {}
    for spec in specs:
        grouped.setdefault((spec.class_level, spec.subject), []).append(spec)

    for key in sorted(grouped):
        subject_specs = grouped[key]
        series_groups: dict[str, list[BookSpec]] = {}
        for spec in subject_specs:
            series_groups.setdefault(_series_key(spec.title), []).append(spec)

        best_series = max(
            series_groups.values(),
            key=lambda items: (
                max(_book_priority(item.title) for item in items),
                len({_part_key(item.title) for item in items}),
                max(item.chapter_count for item in items),
            ),
        )

        parts: dict[str, list[BookSpec]] = {}
        for spec in best_series:
            parts.setdefault(_part_key(spec.title), []).append(spec)

        ordered_parts = sorted(parts.items(), key=lambda item: _part_order(item[0]))
        for part_key, options in ordered_parts[:2]:
            del part_key
            canonical_specs.append(
                max(
                    options,
                    key=lambda item: (
                        _book_priority(item.title),
                        item.chapter_count,
                    ),
                )
            )

    return canonical_specs


def _collect_text_assignments(body: str, pattern: re.Pattern[str]) -> dict[int, str]:
    assignments: dict[int, str] = {}
    for match in pattern.finditer(body):
        assignments[int(match.group(1))] = match.group(2)
    return assignments


def _collect_value_assignments(body: str) -> dict[int, tuple[str, int]]:
    assignments: dict[int, tuple[str, int]] = {}
    for match in BOOK_VALUE_PATTERN.finditer(body):
        assignments[int(match.group(1))] = (match.group(2), int(match.group(3)))
    return assignments


def _build_book_source_url(ncert_code: str, chapter_count: int) -> str:
    return f"https://www.ncert.nic.in/textbook.php?{ncert_code}=0-{chapter_count}&ln=en"


def _series_key(title: str) -> str:
    normalized = html.unescape(title).strip()
    normalized = LANGUAGE_SUFFIX_PATTERN.sub("", normalized)
    normalized = URDU_SUFFIX_PATTERN.sub("", normalized)
    normalized = PART_SUFFIX_PATTERN.sub("", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip(" -")
    return normalized.casefold()


def _part_key(title: str) -> str:
    match = PART_SUFFIX_PATTERN.search(title)
    if not match:
        return "part-0"
    return f"part-{match.group(1).casefold()}"


def _part_order(part_key: str) -> tuple[int, str]:
    if part_key == "part-0":
        return (0, part_key)
    value = part_key.removeprefix("part-")
    roman = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5}
    if value.isdigit():
        return (int(value), part_key)
    return (roman.get(value, 99), part_key)


def _book_priority(title: str) -> int:
    normalized = html.unescape(title).strip()
    score = 0
    if not LANGUAGE_SUFFIX_PATTERN.search(normalized):
        score += 4
    if not URDU_SUFFIX_PATTERN.search(normalized):
        score += 3
    if PART_SUFFIX_PATTERN.search(normalized):
        score += 1
    return score


if __name__ == "__main__":
    main()
