from datetime import datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    player_name: Mapped[str | None] = mapped_column(String(20), nullable=True)
    affinity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chat_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chat_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    current_scene_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="SCENE_INTRO"
    )
    emotion: Mapped[str] = mapped_column(String(16), nullable=False, default="NEUTRAL")
    is_started: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_ended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_affinity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    min_affinity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ending_narrative: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    triggered_events: Mapped[list["TriggeredEvent"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    emotion: Mapped[str | None] = mapped_column(String(16), nullable=True)
    scene_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    affinity_after: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped[Session] = relationship(back_populates="messages")
    embedding: Mapped["MessageEmbedding | None"] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        uselist=False,
    )

    __table_args__ = (
        Index("ix_messages_session_created", "session_id", "created_at"),
    )


class TriggeredEvent(Base):
    __tablename__ = "triggered_events"

    session_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped[Session] = relationship(back_populates="triggered_events")


class MessageEmbedding(Base):
    __tablename__ = "message_embeddings"

    message_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        primary_key=True,
    )
    session_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(4096), nullable=False)

    message: Mapped[Message] = relationship(back_populates="embedding")

    __table_args__ = (
        Index(
            "ix_message_embeddings_session",
            "session_id",
        ),
    )
