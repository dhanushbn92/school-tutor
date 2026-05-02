"""Syllabus board constants.

Boards are tracked as plain strings on `School.board` and `Subject.board`
rather than a Board model — small enough that an enum / table would be
over-engineering. The list lives here so signup validation, subject
creation endpoints, and the frontend dropdown all share one source.

Adding a new board (e.g. when CISCE materials get loaded) is two-step:
  1. Append to `VALID_BOARDS` here, push backend.
  2. Frontend rebuild picks it up via `GET /me` or a future
     `GET /curriculum/boards` endpoint.
"""

# Order matters for UI presentation — most-common-first so the dropdown
# default behaviour ("just press enter on the highlighted option") gives
# the right answer for most signups.
VALID_BOARDS: tuple[str, ...] = (
    "CBSE",
    "NIOS",
    "ICSE",
    "State Board",
    "Other",
)


def is_valid_board(value: str) -> bool:
    """Case-sensitive membership check. The frontend dropdown uses these
    exact strings, so any inbound payload that doesn't match one of them
    is a client bug we should reject loudly."""
    return value in VALID_BOARDS
