from pydantic import BaseModel, Field


class SummaryDiagramBranch(BaseModel):
    label: str = Field(min_length=2, max_length=60)
    details: list[str] = Field(default_factory=list, max_length=5)


class SummaryDiagram(BaseModel):
    """Inline mind-map: one central term plus 3-5 branches. Used as a quick
    visual for either the whole chapter (overview_diagram) or a single
    section (sections[*].diagram)."""

    title: str = Field(min_length=3, max_length=120)
    central_term: str = Field(min_length=2, max_length=60)
    branches: list[SummaryDiagramBranch] = Field(min_length=3, max_length=5)


class SummarySection(BaseModel):
    heading: str = Field(min_length=3, max_length=120)
    bullets: list[str] = Field(min_length=3, max_length=8, description="Plain-language facts/concepts in this section.")
    diagram: SummaryDiagram | None = Field(
        default=None,
        description="Optional inline mind-map for this section. Include only when a visual really helps.",
    )


class GlossaryTerm(BaseModel):
    term: str = Field(min_length=2, max_length=80)
    definition: str = Field(min_length=10, max_length=300)


class ChapterSummaryOutput(BaseModel):
    """Student-facing chapter summary. Bullet-point sections plus mind maps."""

    title: str = Field(min_length=3, max_length=200)
    intro: str = Field(
        min_length=20,
        max_length=600,
        description="2-3 sentence hook explaining what the chapter is about.",
    )
    overview_diagram: SummaryDiagram = Field(
        description="Whole-chapter mind map: central topic plus the main branches.",
    )
    sections: list[SummarySection] = Field(min_length=3, max_length=10)
    key_takeaways: list[str] = Field(min_length=3, max_length=8)
    glossary: list[GlossaryTerm] = Field(min_length=3, max_length=15)
