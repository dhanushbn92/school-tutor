"""LLM-extract a topic-specific text slice from the chapter for each Topic.

We send the FULL chapter text (capped at ~40k chars to stay under the
provider's TPM limit) plus the topic name + description, and ask the LLM to
return the verbatim sentences that cover that topic. The result populates
`Topic.full_text`, which the AI tutor's RAG pipeline uses as the context
for topic-scoped chat sessions.

Two providers supported:
- `--provider groq` (default) — uses the project's configured LLM provider
  (Groq llama-3.3-70b on the free tier).
- `--provider claude` — uses Anthropic's Claude 3.5 Sonnet via the
  `anthropic` SDK. Requires ANTHROPIC_API_KEY in the environment / .env.

Usage:
    .venv/Scripts/python.exe -m scripts.extract_topic_texts
    .venv/Scripts/python.exe -m scripts.extract_topic_texts --chapter-id 58
    .venv/Scripts/python.exe -m scripts.extract_topic_texts \
        --provider claude --class-level 6 --subject Science
"""
import argparse
import json
import logging
import os
import time

from pydantic import ValidationError
from sqlalchemy import select

from app.db.session import SessionLocal
from app.llm import LLMError, get_llm_provider
from app.llm.schemas.topic_text import TopicTextOutput
from app.models.curriculum import Book, Chapter, SchoolClass, Subject, Topic


log = logging.getLogger(__name__)


_MAX_CHAPTER_CHARS = 40_000

_SYSTEM_PROMPT = """\
You are a CBSE/NCERT curriculum analyst. Given a single chapter from an NCERT
textbook plus the name + description of one topic in that chapter, return the
verbatim sentences and paragraphs from the chapter that cover that topic.

Strict rules:
1. Quote the chapter text VERBATIM — copy original sentences and paragraphs.
   Do NOT paraphrase, summarise, or add new commentary.
2. Include only sentences that explain or are about the given topic. Skip
   sentences that belong to a different topic.
3. Keep the order in which sentences appear in the chapter.
4. If the topic genuinely spans most of the chapter, you may return up to
   ~3000 words. Otherwise pick a focused 200-1500 word slice.
5. Output strictly valid JSON: {"text": "..."}. No prose outside the JSON.
"""


def _user_prompt(*, topic_name: str, topic_description: str | None, chapter_text: str) -> str:
    desc = topic_description or ""
    if len(chapter_text) > _MAX_CHAPTER_CHARS:
        chapter_text = chapter_text[:_MAX_CHAPTER_CHARS] + "\n…[truncated]"
    return f"""\
Topic name: {topic_name}
Topic description: {desc}

Full chapter text (your only source of truth):
<<<CHAPTER_TEXT_START>>>
{chapter_text}
<<<CHAPTER_TEXT_END>>>

Return the verbatim sentences from the chapter that cover this topic, as JSON.
"""


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapter-id", type=int, default=None)
    parser.add_argument("--class-level", type=int, default=None)
    parser.add_argument("--subject", default=None)
    parser.add_argument("--overwrite", action="store_true",
                        help="Replace topic.full_text even if already populated.")
    parser.add_argument(
        "--provider",
        choices=["groq", "claude"],
        default="groq",
        help=(
            "LLM provider for extraction. 'groq' = the configured project provider; "
            "'claude' = Anthropic Claude (requires ANTHROPIC_API_KEY)."
        ),
    )
    parser.add_argument(
        "--claude-model",
        default="claude-sonnet-4-5",
        help="Anthropic model name when --provider=claude.",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        topic_stmt = select(Topic).join(Chapter, Topic.chapter_id == Chapter.id)
        if args.chapter_id is not None:
            topic_stmt = topic_stmt.where(Topic.chapter_id == args.chapter_id)
        elif args.class_level is not None and args.subject is not None:
            topic_stmt = (
                topic_stmt.join(Book, Chapter.book_id == Book.id)
                .join(Subject, Book.subject_id == Subject.id)
                .join(SchoolClass, Subject.class_id == SchoolClass.id)
                .where(SchoolClass.level == args.class_level, Subject.name == args.subject)
            )
        topics = list(db.scalars(topic_stmt.order_by(Topic.chapter_id, Topic.id)))

    print(f"Found {len(topics)} topics. Provider={args.provider}. Starting extraction…")
    extract = _build_extractor(args)
    written = 0
    skipped_existing = 0
    errors = 0

    for topic_ref in topics:
        with SessionLocal() as db:
            topic = db.get(Topic, topic_ref.id)
            if topic is None:
                continue
            if topic.full_text and not args.overwrite:
                skipped_existing += 1
                continue
            chapter = db.get(Chapter, topic.chapter_id)
            text = chapter.full_text or ""
            if not text.strip():
                log.warning("ch %s no full_text; skipping topic %s", chapter.id, topic.id)
                continue

            log.info("topic %s '%s' (ch %s) — calling %s", topic.id, topic.name, chapter.id, args.provider)
            t0 = time.time()
            try:
                extracted_text = extract(
                    topic_name=topic.name,
                    topic_description=topic.description,
                    chapter_text=text,
                )
            except LLMError as exc:
                log.error("topic %s LLM error: %s", topic.id, exc)
                errors += 1
                continue
            elapsed = time.time() - t0
            topic.full_text = extracted_text.strip()
            db.commit()
            written += 1
            log.info(
                "topic %s '%s' wrote %s chars in %.1fs",
                topic.id,
                topic.name,
                len(topic.full_text),
                elapsed,
            )

    print()
    print(f"Done. wrote={written}, skipped_existing={skipped_existing}, errors={errors}")


# ---- provider adapters ----

def _build_extractor(args):
    """Returns a callable (topic_name, topic_description, chapter_text) -> str."""
    if args.provider == "claude":
        return _build_claude_extractor(args.claude_model)
    return _build_groq_extractor()


def _build_groq_extractor():
    provider = get_llm_provider()

    def call(*, topic_name, topic_description, chapter_text):
        result = provider.generate_structured(
            system=_SYSTEM_PROMPT,
            user=_user_prompt(
                topic_name=topic_name,
                topic_description=topic_description,
                chapter_text=chapter_text,
            ),
            response_model=TopicTextOutput,
            temperature=0.1,
        )
        return result.text

    return call


def _build_claude_extractor(model: str):
    """Anthropic Claude path. Imports lazily so the dependency is only loaded
    when the user opts in via --provider claude."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit(
            "ANTHROPIC_API_KEY is not set. Add it to your environment or .env "
            "file before running with --provider claude."
        )
    try:
        import anthropic  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "The 'anthropic' Python package is required for --provider claude. "
            "Install it with: pip install anthropic"
        ) from exc

    client = anthropic.Anthropic(api_key=api_key)

    def call(*, topic_name, topic_description, chapter_text):
        # Ask Claude to return JSON matching TopicTextOutput's schema. Claude
        # honours JSON instructions reliably; we still validate via Pydantic
        # to catch any drift.
        user_prompt = _user_prompt(
            topic_name=topic_name,
            topic_description=topic_description,
            chapter_text=chapter_text,
        ) + (
            "\n\nReturn ONLY a single valid JSON object matching this schema, "
            "no prose, no markdown fences:\n"
            f"{json.dumps(TopicTextOutput.model_json_schema())}"
        )
        try:
            message = client.messages.create(
                model=model,
                max_tokens=8000,
                temperature=0.1,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except anthropic.AnthropicError as exc:
            raise LLMError(f"Claude API error: {exc}") from exc

        # `message.content` is a list of content blocks; we expect a single
        # text block for our prompt shape.
        content_text = "".join(
            block.text for block in message.content if getattr(block, "type", None) == "text"
        ).strip()
        # Claude sometimes wraps JSON in ```json … ``` despite the
        # instruction; strip fences just in case.
        if content_text.startswith("```"):
            content_text = content_text.strip("`")
            if content_text.lower().startswith("json"):
                content_text = content_text[4:].strip()
        try:
            data = json.loads(content_text)
            parsed = TopicTextOutput.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise LLMError(f"Claude returned invalid JSON: {exc}") from exc
        return parsed.text

    return call


if __name__ == "__main__":
    main()
