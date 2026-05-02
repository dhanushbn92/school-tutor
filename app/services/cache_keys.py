import hashlib
import json
from typing import Any


def build_generation_cache_key(
    *,
    content_type: str,
    academic_year: str,
    class_level: int,
    subject_id: int | None,
    chapter_id: int | None,
    topic_id: int | None,
    prompt: str | None,
    options: dict[str, Any] | None,
) -> str:
    payload = {
        "content_type": content_type,
        "academic_year": academic_year,
        "class_level": class_level,
        "subject_id": subject_id,
        "chapter_id": chapter_id,
        "topic_id": topic_id,
        "prompt": prompt or "",
        "options": options or {},
        "version": 1,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

