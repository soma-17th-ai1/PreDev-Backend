from collections.abc import AsyncIterator
from functools import lru_cache

from openai import AsyncOpenAI

from app.config import get_settings


@lru_cache(maxsize=1)
def get_client() -> AsyncOpenAI:
    settings = get_settings()
    return AsyncOpenAI(api_key=settings.solar_api_key, base_url=settings.solar_base_url)


async def embed_passage(text: str) -> list[float]:
    settings = get_settings()
    client = get_client()
    resp = await client.embeddings.create(
        model=settings.embedding_model,
        input=text,
    )
    return list(resp.data[0].embedding)


async def embed_query(text: str) -> list[float]:
    settings = get_settings()
    client = get_client()
    resp = await client.embeddings.create(
        model=settings.embedding_query_model,
        input=text,
    )
    return list(resp.data[0].embedding)


async def chat_complete_json(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    max_tokens: int | None = 512,
) -> str:
    """One-shot chat completion. Caller is responsible for prompting JSON output."""

    settings = get_settings()
    client = get_client()
    resp = await client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""


async def chat_stream(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.7,
    max_tokens: int | None = 1024,
) -> AsyncIterator[str]:
    """Stream chat completion deltas as plain text chunks."""

    settings = get_settings()
    client = get_client()
    stream = await client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content


async def health_check() -> bool:
    """Lightweight check — try to list models. Returns True on success."""

    try:
        client = get_client()
        await client.models.list()
        return True
    except Exception:
        return False
