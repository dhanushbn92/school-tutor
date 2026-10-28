"""Add the uppercase EXTRA_CONTENT label to generatedcontenttype

Revision ID: 20261016_0033
Revises: 20261016_0032
Create Date: 2026-10-16

Migration 20260429_0021 added the label in lowercase ('extra_content'), but
SQLAlchemy maps a Python StrEnum column to its member NAME, so the app always
sends 'EXTRA_CONTENT' (as every other label in this enum is stored). On
Postgres that made every query filtering by this type fail with
"invalid input value for enum", which returned HTTP 500 for
`GET /generated-content?content_type=extra_content` — i.e. the "Extra reading"
tab errored on every chapter page, and platform-admin PDF/DOCX uploads could not
be saved.

Adds the correct label. The stray lowercase label is left in place (Postgres
cannot drop enum values) and is harmless; no rows were ever stored under it.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20261016_0033"
down_revision: Union[str, None] = "20261016_0032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block.
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE generatedcontenttype ADD VALUE IF NOT EXISTS 'EXTRA_CONTENT'"
        )


def downgrade() -> None:
    # Postgres cannot drop an enum value without recreating the type, and the
    # value is required by the application, so downgrade is a no-op.
    pass
