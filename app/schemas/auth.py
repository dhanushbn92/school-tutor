from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.school import UserRole


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserRead(BaseModel):
    id: int
    email: EmailStr
    role: UserRole
    school_id: int | None
    full_name: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class SchoolSignupRequest(BaseModel):
    """Public school onboarding. Creates a School and a school_admin User."""

    school_name: str = Field(min_length=3, max_length=200)
    # Validated against `app.core.boards.VALID_BOARDS` at the route level
    # rather than via `Literal[...]` here so adding a new board is a
    # single-line constants change, no schema regen required.
    board: str = Field(default="CBSE", max_length=20)
    address: str | None = Field(default=None, max_length=2000)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=40)

    admin_email: EmailStr
    admin_password: str = Field(min_length=8, max_length=128)
    admin_full_name: str = Field(min_length=2, max_length=200)


class SchoolSignupResponse(BaseModel):
    user: UserRead
    school_id: int
    token: TokenResponse


class IndividualSignupRequest(BaseModel):
    """Public B2C onboarding. Creates a user, a personal 'school of one',
    a section, a student row, and an active enrollment so all assessment +
    submission + mastery code paths work unchanged."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=200)
    class_level: int = Field(ge=6, le=10, description="Class to follow, 6–10 in MVP.")
    academic_year_id: int | None = Field(
        default=None,
        description="Academic year. Defaults to the current one if omitted.",
    )


class IndividualSignupResponse(BaseModel):
    user: UserRead
    school_id: int
    section_id: int
    student_id: int
    token: TokenResponse


class ParentSignupRequest(BaseModel):
    """Public parent / guardian onboarding (Stage 6 of the
    child-centric roadmap). Differs from IndividualSignupRequest in
    two ways:
      - No `class_level` / `academic_year_id` — a parent doesn't have
        a curriculum scope of their own.
      - `invite_code` — required. Created by the learner via
        `POST /me/parent-invite-codes` and handed to the parent. The
        signup flow consumes the code and creates the parent ↔ child
        link in the same transaction as the user row, so a
        half-finished signup can't leave an orphaned parent account.
    """

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=200)
    # Eight uppercase chars from the unambiguous set; whitespace is
    # stripped + upper-cased server-side so a parent typing "abc 123 de"
    # still resolves cleanly.
    invite_code: str = Field(min_length=8, max_length=16)


class ParentSignupResponse(BaseModel):
    user: UserRead
    child_user_id: int
    token: TokenResponse
