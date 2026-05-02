"""Schemas for the platform-admin tenants surface (`/platform/...`).

These are *read* shapes only — the platform team views and toggles
activation, but doesn't edit school details (that stays in the school
admin's hands).
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PlatformSchoolSummary(BaseModel):
    """One row in the schools list."""

    id: int
    name: str
    board: str
    brand_name: str | None
    is_active: bool
    student_count: int
    teacher_count: int
    section_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlatformSectionSummary(BaseModel):
    id: int
    name: str
    class_level: int | None
    class_display_name: str | None
    academic_year: str | None
    class_teacher_name: str | None
    student_count: int


class PlatformTeacherSummary(BaseModel):
    id: int
    full_name: str
    email: str
    qualification: str | None
    sections_count: int
    is_active: bool


class PlatformStudentSummary(BaseModel):
    id: int
    full_name: str
    roll_number: str | None
    section_name: str | None
    class_level: int | None
    has_login: bool
    is_active: bool


class PlatformSchoolOverview(BaseModel):
    """Everything a platform admin needs to see for one school in one shot."""

    id: int
    name: str
    board: str
    address: str | None
    contact_email: str | None
    contact_phone: str | None
    brand_name: str | None
    is_active: bool
    is_personal: bool
    created_at: datetime

    student_count: int
    teacher_count: int
    section_count: int

    sections: list[PlatformSectionSummary]
    teachers: list[PlatformTeacherSummary]
    students: list[PlatformStudentSummary]


class PlatformLearnerSummary(BaseModel):
    """One row in the individual-learners list."""

    user_id: int
    full_name: str
    email: str
    is_active: bool
    class_level: int | None
    signup_date: datetime
    submissions_count: int
    average_percentage: float | None


class PlatformLearnerSubmission(BaseModel):
    submission_id: int
    assessment_id: int
    assessment_title: str
    chapter_id: int | None
    chapter_title: str | None
    score: float | None
    max_marks: float | None
    percentage: float | None
    submitted_at: datetime | None
    evaluated_at: datetime | None
    status: str


class PlatformLearnerOverview(BaseModel):
    """A single learner's profile + activity for the platform admin view."""

    user_id: int
    full_name: str
    email: str
    is_active: bool
    signup_date: datetime
    last_login_at: datetime | None
    class_level: int | None
    class_display_name: str | None
    school_id: int

    submissions_count: int
    average_percentage: float | None
    last_activity_at: datetime | None
    average_mastery: float | None

    recent_submissions: list[PlatformLearnerSubmission]


class ActivationToggle(BaseModel):
    """Body for the enable/disable endpoints."""

    is_active: bool
