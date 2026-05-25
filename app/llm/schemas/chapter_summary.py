from typing import Union

from pydantic import BaseModel, Field


class SummaryDiagramBranch(BaseModel):
    """One node in the mind-map tree. `details` is recursive: each
    entry is either a plain string (a leaf — a single fact / point)
    or another `SummaryDiagramBranch` object (a sub-branch that
    itself has children). The recursion lets the LLM emit mind maps
    as deep as the chapter content warrants — flat for simple
    topics, multi-level for richly-structured ones.

    Backward compatibility: chapter summaries generated before this
    change shipped only string details. Strings remain valid here
    (they're one half of the union), so existing data still loads
    without any migration.
    """

    label: str = Field(min_length=2, max_length=60)
    # Forward reference to the model name as a string so Pydantic can
    # resolve the self-reference. We use `typing.Union` rather than
    # the PEP 604 `str | "..."` syntax because the latter fails to
    # evaluate forward refs at module-load time on Python 3.12 — the
    # `|` operator there expects both sides to be evaluated types
    # before being combined.
    details: list[Union[str, "SummaryDiagramBranch"]] = Field(
        default_factory=list,
        max_length=8,
        description=(
            "Children of this branch. Each entry is either a plain "
            "string (leaf — a single fact or point) or a nested "
            "{label, details} object (sub-branch that itself has "
            "children). Use the nested form when the content has "
            "natural hierarchy; use plain strings for simple flat "
            "lists. Mind maps can go several levels deep when the "
            "chapter genuinely supports it."
        ),
    )


class SummaryDiagram(BaseModel):
    """Inline mind-map: one central term plus 3-5 branches. Used as
    a quick visual for either the whole chapter (overview_diagram)
    or a single section (sections[*].diagram).

    Each branch's `details` can themselves contain nested branches
    (recursively), so the diagram can fan out to multiple levels
    where the content has that depth.
    """

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


# Pydantic 2 needs an explicit rebuild for the self-referential
# SummaryDiagramBranch.details type. Without this the forward
# reference stays unresolved and `model_validate` fails on nested
# children.
SummaryDiagramBranch.model_rebuild()
