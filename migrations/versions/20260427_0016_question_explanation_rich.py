"""Add explanation_rich JSON column to Question

Revision ID: 20260427_0016
Revises: 20260427_0015
Create Date: 2026-04-27

For long-answer / subjective questions where a plain-text explanation is
not enough; teachers/authors can attach structured blocks (text, list,
mind-map, flow-diagram, image) that the frontend renders inline.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260427_0016"
down_revision: Union[str, None] = "20260427_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "questions",
        sa.Column("explanation_rich", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("questions", "explanation_rich")
