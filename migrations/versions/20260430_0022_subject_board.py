"""Add board column to subjects + extend unique constraint

Revision ID: 20260430_0022
Revises: 20260429_0021
Create Date: 2026-04-30

Adds a `board` column to the `subjects` table so the platform can host
syllabi for multiple boards (CBSE, NIOS, ICSE, …) side by side. Existing
rows backfill to 'CBSE' (the only board the platform supported until now).

The unique constraint on subjects expands from `(class_id, name, language)`
to `(class_id, name, language, board)` so CBSE Mathematics and NIOS
Mathematics can coexist in the same class.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260430_0022"
down_revision: Union[str, None] = "20260429_0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the column with a server_default so existing rows backfill in
    # one statement; without the default the NOT NULL constraint would
    # fail. We keep the default at the DB level so application code that
    # forgets to set `board` on insert still gets 'CBSE'.
    op.add_column(
        "subjects",
        sa.Column(
            "board",
            sa.String(length=20),
            nullable=False,
            server_default="CBSE",
        ),
    )
    op.create_index("ix_subjects_board", "subjects", ["board"])

    # Swap the unique constraint to include `board`. CBSE and NIOS can
    # both have a "Mathematics" subject under Class 10 once this lands.
    op.drop_constraint(
        "uq_subjects_class_name_language", "subjects", type_="unique"
    )
    op.create_unique_constraint(
        "uq_subjects_class_name_lang_board",
        "subjects",
        ["class_id", "name", "language", "board"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_subjects_class_name_lang_board", "subjects", type_="unique"
    )
    op.create_unique_constraint(
        "uq_subjects_class_name_language",
        "subjects",
        ["class_id", "name", "language"],
    )
    op.drop_index("ix_subjects_board", table_name="subjects")
    op.drop_column("subjects", "board")
