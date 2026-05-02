from pydantic import BaseModel, Field


class ConceptBranch(BaseModel):
    label: str = Field(min_length=2, max_length=60)
    details: list[str] = Field(
        min_length=0,
        max_length=5,
        description="Leaf nodes attached to this branch.",
    )


class DiagramOutput(BaseModel):
    """A radial concept map: one central term + 3-6 branches, each with up to 5 details."""

    title: str = Field(min_length=3, max_length=120)
    central_term: str = Field(min_length=2, max_length=60)
    branches: list[ConceptBranch] = Field(min_length=3, max_length=6)
    outcome_codes_covered: list[str] = Field(default_factory=list)
