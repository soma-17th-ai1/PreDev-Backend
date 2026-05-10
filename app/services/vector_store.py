from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm import solar_client
from app.models.orm import MessageEmbedding


async def store_embedding(
    db: AsyncSession, *, message_id: UUID, session_id: UUID, content: str
) -> None:
    """Compute embedding and persist. Best-effort: failures are swallowed by caller."""

    embedding = await solar_client.embed_passage(content)
    db.add(
        MessageEmbedding(
            message_id=message_id,
            session_id=session_id,
            embedding=embedding,
        )
    )
    await db.commit()


async def search_similar(
    db: AsyncSession, *, session_id: UUID, query_text: str, k: int = 4
) -> list[dict]:
    """Return up to k past messages most similar to query_text within the session.

    The result is a plain list of dicts: [{role, content, similarity}].
    Empty list on any failure.
    """

    try:
        embedding = await solar_client.embed_query(query_text)
    except Exception:
        return []

    sql = text(
        """
        SELECT m.role, m.content,
               1 - (e.embedding <=> CAST(:embedding AS vector)) AS similarity
        FROM message_embeddings e
        JOIN messages m ON m.id = e.message_id
        WHERE e.session_id = :session_id
        ORDER BY e.embedding <=> CAST(:embedding AS vector)
        LIMIT :k
        """
    )
    rows = await db.execute(
        sql,
        {
            "embedding": str(embedding),
            "session_id": str(session_id),
            "k": k,
        },
    )
    return [
        {"role": r.role, "content": r.content, "similarity": float(r.similarity)}
        for r in rows
    ]
