"""Tenant kill-switch — School.is_active

Revision ID: 20260428_0020
Revises: 20260428_0019
Create Date: 2026-04-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260428_0020"
down_revision: Union[str, None] = "20260428_0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New tenant-level activation flag. Existing schools are active by default
    # so the migration is non-disruptive — only platform admins toggling this
    # field can lock a tenant out.
    op.add_column(
        "schools",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.create_index(
        "ix_schools_is_active",
        "schools",
        ["is_active"],
    )


def downgrade() -> None:
    op.drop_index("ix_schools_is_active", table_name="schools")
    op.drop_column("schools", "is_active")
