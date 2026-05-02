from app.services.cache_keys import build_generation_cache_key


def test_generation_cache_key_is_stable_for_same_payload():
    first = build_generation_cache_key(
        content_type="quiz",
        academic_year="2026-27",
        class_level=8,
        subject_id=1,
        chapter_id=2,
        topic_id=None,
        prompt="Generate 10 questions",
        options={"difficulty": "medium", "count": 10},
    )
    second = build_generation_cache_key(
        content_type="quiz",
        academic_year="2026-27",
        class_level=8,
        subject_id=1,
        chapter_id=2,
        topic_id=None,
        prompt="Generate 10 questions",
        options={"count": 10, "difficulty": "medium"},
    )

    assert first == second


def test_generation_cache_key_changes_when_topic_changes():
    chapter_level = build_generation_cache_key(
        content_type="simulation",
        academic_year="2026-27",
        class_level=8,
        subject_id=1,
        chapter_id=2,
        topic_id=None,
        prompt=None,
        options={},
    )
    topic_level = build_generation_cache_key(
        content_type="simulation",
        academic_year="2026-27",
        class_level=8,
        subject_id=1,
        chapter_id=2,
        topic_id=5,
        prompt=None,
        options={},
    )

    assert chapter_level != topic_level

