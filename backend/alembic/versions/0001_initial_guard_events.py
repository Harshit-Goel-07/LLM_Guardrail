"""initial guard_events table

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-01 00:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "guard_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("client_id", sa.String(length=128), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("block_threshold", sa.Float(), nullable=False),
        sa.Column("categories", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("heuristic_hits", sa.JSON(), nullable=True),
        sa.Column("semantic_matches", sa.JSON(), nullable=True),
        sa.Column("breakdown", sa.JSON(), nullable=True),
        sa.Column("embedding_backend", sa.String(length=32), nullable=True),
        sa.Column("llm_provider", sa.String(length=32), nullable=True),
        sa.Column("llm_model", sa.String(length=64), nullable=True),
        sa.Column("llm_response", sa.Text(), nullable=True),
        sa.Column("detection_latency_ms", sa.Float(), nullable=False),
        sa.Column("flagged_false_positive", sa.Boolean(), nullable=False),
        sa.Column("flagged_false_negative", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_guard_events_created_at", "guard_events", ["created_at"])
    op.create_index("ix_guard_events_client_id", "guard_events", ["client_id"])
    op.create_index("ix_guard_events_decision", "guard_events", ["decision"])
    op.create_index("ix_guard_events_risk_score", "guard_events", ["risk_score"])


def downgrade() -> None:
    op.drop_index("ix_guard_events_risk_score", table_name="guard_events")
    op.drop_index("ix_guard_events_decision", table_name="guard_events")
    op.drop_index("ix_guard_events_client_id", table_name="guard_events")
    op.drop_index("ix_guard_events_created_at", table_name="guard_events")
    op.drop_table("guard_events")
