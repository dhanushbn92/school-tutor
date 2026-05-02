from pydantic import BaseModel, Field


class TopicTextOutput(BaseModel):
    """LLM extracts the verbatim slice of the chapter that covers a single
    topic. We keep the original wording so the AI tutor's RAG context stays
    truthful to the textbook."""

    text: str = Field(
        min_length=20,
        max_length=20_000,
        description=(
            "The chapter sentences/paragraphs that cover this topic, in order. "
            "Quote the original wording — do NOT paraphrase or summarise."
        ),
    )
