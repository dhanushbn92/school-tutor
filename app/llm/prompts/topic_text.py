"""LLM prompts for slicing per-topic verbatim text out of a chapter.

Used by the AI tutor's RAG pipeline: when a student opens a topic-scoped
chat, we feed the LLM the topic-specific slice (instead of the whole
chapter) so the answers stay focused. The slice is populated on the
`Topic.full_text` column.

The prompts here mirror the ones in `scripts/extract_topic_texts.py`;
extracting them into a shared module so the platform-admin UI ingestion
service and the script both call the same prompt.
"""

# Hard cap on chapter text we send to the LLM per slicing request. The
# free Groq tier currently sits at 12,000 tokens-per-minute on
# llama-3.3-70b. Empirically, llama tokenisers run ~3 chars/token on
# English textbook prose, so we cap chars at 18,000 (~6,000 tokens)
# leaving ~6,000 tokens of TPM budget for the system prompt + topic
# metadata + response. The script-based pipeline uses 40,000 because it
# runs serially over many minutes; the synchronous service path here
# fans 8 topics into a few minutes and would otherwise blow the limit.
MAX_CHAPTER_CHARS = 18_000


TOPIC_TEXT_SYSTEM_PROMPT = """\
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


def build_topic_text_user_prompt(
    *,
    topic_name: str,
    topic_description: str | None,
    chapter_text: str,
) -> str:
    """Compose the user-prompt for one topic. Truncates chapter text to
    `MAX_CHAPTER_CHARS` so we don't blow past provider token limits."""
    desc = topic_description or ""
    if len(chapter_text) > MAX_CHAPTER_CHARS:
        chapter_text = chapter_text[:MAX_CHAPTER_CHARS] + "\n…[truncated]"
    return f"""\
Topic name: {topic_name}
Topic description: {desc}

Full chapter text (your only source of truth):
<<<CHAPTER_TEXT_START>>>
{chapter_text}
<<<CHAPTER_TEXT_END>>>

Return the verbatim sentences from the chapter that cover this topic, as JSON.
"""
