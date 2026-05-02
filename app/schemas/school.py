from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SchoolRead(BaseModel):
    id: int
    name: str
    board: str
    address: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    brand_name: str | None = None
    logo_url: str | None = None
    is_personal: bool = False
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class SchoolUpdate(BaseModel):
    """Partial update of school details (school admin only)."""

    name: str | None = None
    board: str | None = None
    address: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    brand_name: str | None = None
    logo_url: str | None = None


class CreateSectionRequest(BaseModel):
    class_id: int
    academic_year_id: int
    name: str = Field(min_length=1, max_length=10)
    class_teacher_id: int | None = None


class CreateEnrollmentRequest(BaseModel):
    student_id: int
    section_id: int
    academic_year_id: int


class TeacherRead(BaseModel):
    id: int
    user_id: int
    school_id: int
    full_name: str
    qualification: str | None

    model_config = ConfigDict(from_attributes=True)


class TeacherSubjectsRead(BaseModel):
    """A teacher's explicit subject assignments + a flag for the fallback case.

    `is_explicit=False` means no rows exist yet for this teacher; the UI
    should communicate that "no subject restrictions are configured" and
    offer to add them. `is_explicit=True` means the school admin has opted
    in to per-subject scoping for this teacher and the restriction is in
    force.
    """

    teacher_id: int
    subject_ids: list[int]
    is_explicit: bool


class TeacherSubjectsSet(BaseModel):
    """Replace the full set of subjects assigned to one teacher.

    The endpoint is idempotent — pass the desired subject_ids; we diff
    against what's stored. Pass an empty list to clear all assignments
    (which puts the teacher back into the fallback "all subjects of my
    class-teacher classes" mode).
    """

    subject_ids: list[int] = Field(default_factory=list)


class SectionRead(BaseModel):
    id: int
    school_id: int
    class_id: int
    academic_year_id: int
    name: str
    class_teacher_id: int | None
    class_level: int | None = None
    class_display_name: str | None = None
    academic_year: str | None = None


class StudentRead(BaseModel):
    id: int
    school_id: int
    user_id: int | None = None
    full_name: str
    roll_number: str | None
    dob: date | None
    gender: str | None
    guardian_name: str | None
    guardian_phone: str | None

    model_config = ConfigDict(from_attributes=True)


class EnrollmentRead(BaseModel):
    id: int
    student_id: int
    section_id: int
    academic_year_id: int
    status: str

    model_config = ConfigDict(from_attributes=True)


class CreateTeacherRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    qualification: str | None = None


class CreateStudentRequest(BaseModel):
    full_name: str
    roll_number: str | None = None
    dob: date | None = None
    gender: str | None = None
    guardian_name: str | None = None
    guardian_phone: str | None = None
