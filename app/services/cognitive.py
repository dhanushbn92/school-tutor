"""Cognitive-level grouping helpers.

The platform stores question cognitive level at the canonical 6-level Bloom
granularity (REMEMBER / UNDERSTAND / APPLY / ANALYZE / EVALUATE / CREATE).
Most user-facing surfaces show a coarser 3-bucket view that's easier for
Class 6–10 teachers and students to read.

This module owns the mapping. Keep all business logic that needs to convert
between the two granularities going through `to_bucket()` so the rule lives
in exactly one place.
"""
from app.models.curriculum import BloomLevel
from app.models.mastery import CognitiveBucket


_BLOOM_TO_BUCKET: dict[BloomLevel, CognitiveBucket] = {
    BloomLevel.REMEMBER: CognitiveBucket.FACTUAL,
    BloomLevel.UNDERSTAND: CognitiveBucket.UNDERSTANDING,
    BloomLevel.APPLY: CognitiveBucket.APPLICATION,
    BloomLevel.ANALYZE: CognitiveBucket.APPLICATION,
    BloomLevel.EVALUATE: CognitiveBucket.APPLICATION,
    BloomLevel.CREATE: CognitiveBucket.APPLICATION,
}


def to_bucket(level: BloomLevel) -> CognitiveBucket:
    """Roll a 6-level Bloom value up to one of FACTUAL/UNDERSTANDING/APPLICATION."""
    return _BLOOM_TO_BUCKET[level]


def bucket_label(bucket: CognitiveBucket) -> str:
    """Human-friendly label used in API payloads + UI tooltips."""
    return {
        CognitiveBucket.FACTUAL: "Factual",
        CognitiveBucket.UNDERSTANDING: "Understanding",
        CognitiveBucket.APPLICATION: "Application",
    }[bucket]
