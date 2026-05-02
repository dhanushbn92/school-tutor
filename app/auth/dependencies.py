from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.security import AuthError, decode_token
from app.db.session import get_db
from app.models.school import School, User, UserRole


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=True)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        claims = decode_token(token)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id_raw = claims.get("sub")
    if not user_id_raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token")
    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token") from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    # Tenant kill-switch: a school admin/teacher/student of a school the
    # platform team has disabled is rejected here on every request, so an
    # already-issued JWT can't keep them in. Personal schools
    # (is_personal=True) aren't gated this way — for individual learners we
    # rely on user.is_active above, since their "school" is just a
    # bookkeeping shell for their own account.
    if user.school_id is not None:
        school = db.get(School, user.school_id)
        if school is not None and not school.is_personal and not school.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your school has been disabled by the platform team. Please contact support.",
            )
    return user


def _require_role(*roles: UserRole):
    allowed = set(roles)

    def dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(r.value for r in allowed)}",
            )
        return user

    return dep


# --- Single-role guards ---
require_platform_admin = _require_role(UserRole.PLATFORM_ADMIN)
require_school_admin = _require_role(UserRole.SCHOOL_ADMIN)
require_teacher = _require_role(UserRole.TEACHER)
require_student = _require_role(UserRole.STUDENT)
require_individual_learner = _require_role(UserRole.INDIVIDUAL_LEARNER)


# --- Role groups for school-side workflow ---

# Anyone who runs a classroom: school admin or teacher in a school.
require_teacher_or_school_admin = _require_role(UserRole.SCHOOL_ADMIN, UserRole.TEACHER)

# Anyone who can take a quiz / consume catalog content.
# Includes student in a school AND individual learner.
require_learner = _require_role(UserRole.STUDENT, UserRole.INDIVIDUAL_LEARNER)

# Catalog readers — every authenticated non-platform role. Used for catalog
# browsing and quiz-from-bank where school admins, teachers, students, and
# individuals all need access.
require_catalog_reader = _require_role(
    UserRole.SCHOOL_ADMIN,
    UserRole.TEACHER,
    UserRole.STUDENT,
    UserRole.INDIVIDUAL_LEARNER,
)


def is_platform_admin(user: User) -> bool:
    return user.role == UserRole.PLATFORM_ADMIN
