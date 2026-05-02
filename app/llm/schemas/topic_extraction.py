from pydantic import BaseModel, Field


class ExtractedTopic(BaseModel):
    name: str = Field(
        min_length=3,
        max_length=120,
        description="Short, title-case topic name (3-8 words). Avoid generic words like 'Introduction'.",
    )
    description: str = Field(
        min_length=10,
        max_length=400,
        description="One- or two-sentence summary of what this topic covers.",
    )


class TopicExtractionOutput(BaseModel):
    topics: list[ExtractedTopic] = Field(
        min_length=3,
        max_length=12,
        description=(
            "Main conceptual topics in the chapter, ordered the way a student "
            "would meet them. Aim for 4-8 topics; merge near-duplicates."
        ),
    )
