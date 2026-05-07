"""init schema with pgvector

Revision ID: 0001
Revises:
Create Date: 2026-05-07
"""
from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    op.create_table(
        "sessions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("player_name", sa.String(20), nullable=True),
        sa.Column("affinity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chat_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chat_limit", sa.Integer(), nullable=False, server_default="50"),
        sa.Column(
            "current_scene_id",
            sa.String(64),
            nullable=False,
            server_default="SCENE_INTRO",
        ),
        sa.Column("emotion", sa.String(16), nullable=False, server_default="NEUTRAL"),
        sa.Column("is_started", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_ended", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("max_affinity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("min_affinity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ending_narrative", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_active_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("emotion", sa.String(16), nullable=True),
        sa.Column("scene_id", sa.String(64), nullable=True),
        sa.Column("affinity_after", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_messages_session_created",
        "messages",
        ["session_id", "created_at"],
    )

    op.create_table(
        "triggered_events",
        sa.Column(
            "session_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("event_id", sa.String(64), primary_key=True),
        sa.Column(
            "triggered_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "message_embeddings",
        sa.Column(
            "message_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("messages.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "session_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "embedding",
            pgvector.sqlalchemy.Vector(4096),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_message_embeddings_session",
        "message_embeddings",
        ["session_id"],
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_message_embeddings_cosine;")
    op.drop_index("ix_message_embeddings_session", table_name="message_embeddings")
    op.drop_table("message_embeddings")
    op.drop_table("triggered_events")
    op.drop_index("ix_messages_session_created", table_name="messages")
    op.drop_table("messages")
    op.drop_table("sessions")
