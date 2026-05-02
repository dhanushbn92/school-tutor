from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.curriculum import Chapter, Subject, Topic
from app.models.generation import GeneratedContent, GeneratedContentStatus
from app.schemas.generation import GenerateContentRequest
from app.services.cache_keys import build_generation_cache_key
from app.services.curriculum_service import build_curriculum_context


def _resolve_model_name(settings: Settings) -> str:
    if settings.llm_model:
        return settings.llm_model
    provider = settings.llm_provider.lower()
    if provider == "groq":
        return settings.groq_default_model
    if provider == "openai":
        return settings.openai_default_model
    return provider


def create_or_reuse_generated_content(
    db: Session,
    request: GenerateContentRequest,
    *,
    creator_user_id: int | None = None,
) -> GeneratedContent:
    cache_key = build_generation_cache_key(
        content_type=request.content_type.value,
        academic_year=request.academic_year,
        class_level=request.class_level,
        subject_id=request.subject_id,
        chapter_id=request.chapter_id,
        topic_id=request.topic_id,
        prompt=request.prompt,
        options=request.options,
    )

    if not request.force_regenerate:
        existing = db.scalar(select(GeneratedContent).where(GeneratedContent.cache_key == cache_key))
        if existing is not None:
            return existing
    else:
        # Uniqueness is enforced on cache_key at the DB level, so force-regens
        # need a distinct key. Append a timestamp suffix; the original `cache_key`
        # still matches on future non-force requests for a fresh cache hit.
        cache_key = f"{cache_key}-regen-{int(datetime.now(timezone.utc).timestamp() * 1000)}"

    subject = db.get(Subject, request.subject_id)
    chapter = db.get(Chapter, request.chapter_id) if request.chapter_id else None
    topic = db.get(Topic, request.topic_id) if request.topic_id else None
    source_context = None

    if chapter is not None:
        context = build_curriculum_context(db, chapter.id, request.topic_id)
        source_context = context["context_text"] if context else None

    title = request.title or _default_title(request, subject_name=subject.name if subject else None, chapter=chapter, topic=topic)
    settings = get_settings()

    generated = GeneratedContent(
        content_type=request.content_type,
        status=GeneratedContentStatus.PENDING,
        cache_key=cache_key,
        academic_year=request.academic_year,
        class_level=request.class_level,
        subject_id=request.subject_id,
        chapter_id=request.chapter_id,
        topic_id=request.topic_id,
        title=title,
        prompt=request.prompt,
        source_context=source_context,
        request_options=request.options,
        llm_provider=settings.llm_provider,
        llm_model=_resolve_model_name(settings),
        created_by_id=creator_user_id,
    )
    db.add(generated)
    db.commit()
    db.refresh(generated)
    return generated


def _default_title(
    request: GenerateContentRequest,
    *,
    subject_name: str | None,
    chapter: Chapter | None,
    topic: Topic | None,
) -> str:
    parts = [request.content_type.value.replace("_", " ").title(), f"Class {request.class_level}"]
    if subject_name:
        parts.append(subject_name)
    if chapter:
        parts.append(f"Chapter {chapter.chapter_number}: {chapter.title}")
    if topic:
        parts.append(topic.name)
    return " - ".join(parts)

