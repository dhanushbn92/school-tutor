from pydantic import BaseModel, ConfigDict


class ChapterVideoRead(BaseModel):
    id: int
    chapter_id: int
    sequence: int
    title: str
    kind: str
    provider: str
    external_id: str

    model_config = ConfigDict(from_attributes=True)


class FeaturedChapterRead(BaseModel):
    """A chapter that has published video lectures."""

    chapter_id: int
    chapter_number: int
    chapter_title: str
    subject_id: int
    subject_name: str
    video_count: int


class FeaturedVideosRead(BaseModel):
    """What the dashboard needs to promote the video lessons a learner can watch."""

    total_videos: int
    total_chapters: int
    chapters: list[FeaturedChapterRead]
