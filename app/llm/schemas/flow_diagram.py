from typing import Literal

from pydantic import BaseModel, Field


class FlowNode(BaseModel):
    id: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=2, max_length=60)
    detail: str | None = Field(default=None, max_length=240)
    kind: Literal["start", "step", "decision", "end"] = "step"


class FlowEdge(BaseModel):
    src: str = Field(min_length=1, max_length=40, description="ID of the source node.")
    dst: str = Field(min_length=1, max_length=40, description="ID of the destination node.")
    label: str | None = Field(default=None, max_length=40)


class FlowDiagramOutput(BaseModel):
    """A simple directed flow diagram: nodes + edges. Used for processes,
    classification trees, and decision flows. The frontend lays nodes out
    automatically based on edge order; node positions don't need to be
    pre-computed by the author."""

    title: str = Field(min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=400)
    nodes: list[FlowNode] = Field(min_length=2, max_length=20)
    edges: list[FlowEdge] = Field(min_length=1, max_length=40)
    outcome_codes_covered: list[str] = Field(default_factory=list)
