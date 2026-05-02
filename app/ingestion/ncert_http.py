import io
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pypdf import PdfReader


NCERT_TEXTBOOK_PAGE_URL = "https://www.ncert.nic.in/textbook.php?ln=en"
NCERT_REFERER = "https://www.ncert.nic.in/textbook.php"


def fetch_text(url: str, *, timeout: int = 30, retries: int = 3) -> str:
    payload = download_binary(
        url,
        timeout=timeout,
        retries=retries,
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    return payload.decode("utf-8", errors="ignore")


def download_pdf(url: str, *, timeout: int = 30, retries: int = 3) -> bytes:
    payload = download_binary(
        url,
        timeout=timeout,
        retries=retries,
        headers={
            "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
        },
    )
    if b"%PDF" not in payload[:1024]:
        raise ValueError(f"URL did not return a PDF: {url}")
    return payload


def download_binary(url: str, *, timeout: int = 30, retries: int = 3, headers: dict[str, str] | None = None) -> bytes:
    request_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/135.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": NCERT_REFERER,
        "Connection": "close",
    }
    if headers:
        request_headers.update(headers)
    last_error: Exception | None = None
    for attempt in range(retries):
        request = Request(url, headers=request_headers)
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except (HTTPError, URLError, ConnectionError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt == retries - 1:
                break
            time.sleep(1.5 * (attempt + 1))
    assert last_error is not None
    raise last_error


def extract_pdf_text(pdf_bytes: bytes) -> tuple[str, int, list[str]]:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    page_texts = [(page.extract_text() or "").strip() for page in reader.pages]
    text = "\n\n".join(page_text for page_text in page_texts if page_text)
    return text, len(reader.pages), page_texts


_FILENAME_PATTERN = re.compile(r"Chapter\s+\d+\.indd", re.IGNORECASE)
_CHAPTER_LINE_PATTERN = re.compile(r"^\s*(\d+)\s+(.+?)\s*$")
_CHAPTER_MARKER_PATTERN = re.compile(r"\bChapter\b", re.IGNORECASE)
_TITLE_WITH_NUMBER_PATTERN = re.compile(r"^(?P<title>.+?)\s*(?P<number>\d+)\s*(?:Chapter\b)?\s*$", re.IGNORECASE)


def extract_chapter_title_from_pdf(pdf_bytes: bytes, chapter_number: int) -> str:
    _, _, page_texts = extract_pdf_text(pdf_bytes)
    if page_texts:
        title = extract_chapter_title_from_text(page_texts[0], chapter_number)
        if title != f"Chapter {chapter_number}":
            return title

    text, _, _ = extract_pdf_text(pdf_bytes)
    return extract_chapter_title_from_text(text, chapter_number)


def extract_chapter_title_from_text(text: str, chapter_number: int) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    footer_index = next((index for index, line in enumerate(lines) if _FILENAME_PATTERN.search(line)), len(lines))
    header_lines = lines[:footer_index]

    title = _extract_title_from_opening_lines(header_lines, chapter_number)
    if title:
        return title

    title = _extract_title_near_chapter_marker(header_lines, chapter_number)
    if title:
        return title

    for index in range(footer_index - 1, -1, -1):
        line = lines[index]
        if line.strip() == str(chapter_number):
            for previous_index in range(index - 1, -1, -1):
                previous = lines[previous_index].strip()
                if previous:
                    return _cleanup_chapter_title(previous)

        match = _CHAPTER_LINE_PATTERN.match(line)
        if match and int(match.group(1)) == chapter_number:
            title_parts = [match.group(2).strip()]
            for next_line in lines[index + 1 : footer_index]:
                if next_line.strip() == str(chapter_number):
                    break
                if _FILENAME_PATTERN.search(next_line):
                    break
                if re.match(r"^\s*\d+\.\d+", next_line):
                    break
                if next_line.lower().startswith("reprint"):
                    break
                if next_line.lower().startswith("chapter "):
                    break
                title_parts.append(next_line)
            return _cleanup_chapter_title(" ".join(title_parts).strip())

    return f"Chapter {chapter_number}"


def _extract_title_from_opening_lines(lines: list[str], chapter_number: int) -> str | None:
    if not lines:
        return None

    opening_lines = lines[:3]
    if opening_lines and opening_lines[0] == str(chapter_number):
        opening_lines = opening_lines[1:]
    if opening_lines and opening_lines[0].lower() == "chapter":
        opening_lines = opening_lines[1:]

    for size in range(min(3, len(opening_lines)), 0, -1):
        candidate = _cleanup_chapter_title(" ".join(opening_lines[:size]))
        matched = _TITLE_WITH_NUMBER_PATTERN.match(candidate)
        if matched and int(matched.group("number")) == chapter_number:
            return _cleanup_chapter_title(matched.group("title"))
    return None


def _extract_title_near_chapter_marker(lines: list[str], chapter_number: int) -> str | None:
    if not lines:
        return None

    for index in range(len(lines)):
        for window in range(3, 0, -1):
            chunk = _cleanup_chapter_title(" ".join(lines[index : index + window]))
            matched = _TITLE_WITH_NUMBER_PATTERN.match(chunk)
            if matched and int(matched.group("number")) == chapter_number:
                title = _cleanup_chapter_title(matched.group("title"))
                if title and not _looks_like_running_text(title):
                    return title

    if len(lines) >= 2 and lines[0] == str(chapter_number) and lines[1].lower() == "chapter":
        for line in lines[2:20]:
            candidate = _cleanup_chapter_title(line)
            if _looks_like_title_line(candidate):
                return candidate
    return None


def _looks_like_title_line(value: str) -> bool:
    if not value or len(value) > 80:
        return False
    if value.endswith((".", "?", "!", ":")):
        return False
    words = [word for word in re.split(r"\s+", value) if word]
    if not words:
        return False
    alpha_words = [word for word in words if any(char.isalpha() for char in word)]
    if not alpha_words:
        return False
    titleish = sum(1 for word in alpha_words if word[:1].isupper())
    return titleish >= max(1, len(alpha_words) - 1)


def _looks_like_running_text(value: str) -> bool:
    if len(value) > 90:
        return True
    lowered = value.lower()
    return any(
        phrase in lowered
        for phrase in (
            " lives ",
            " are ",
            " is ",
            " was ",
            " were ",
            " have ",
            " has ",
            " they ",
            " their ",
        )
    )


def _cleanup_chapter_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title).strip()
    title = title.replace("  ", " ")
    return title
