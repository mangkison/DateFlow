"""
크롤링 요약 텍스트를 임베딩하여 Qdrant에 저장한다.
임베딩 모델: text-embedding-3-small (1536차원)
"""
import uuid

from openai import AsyncOpenAI
from qdrant_client.models import PointStruct

from app.core.config import settings
from app.db.qdrant import COLLECTION_NAME, get_qdrant

_openai_client: AsyncOpenAI | None = None


def _get_openai() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


async def embed_text(text: str) -> list[float]:
    client = _get_openai()
    resp = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return resp.data[0].embedding


async def upsert_place_vector(
    place_id: uuid.UUID,
    summary: str,
    metadata: dict,
) -> uuid.UUID:
    """
    summary를 임베딩하여 Qdrant에 저장하고 포인트 ID를 반환한다.
    metadata: {name, category, area, atmosphere_tags}
    """
    vector = await embed_text(summary)
    point_id = uuid.uuid5(uuid.NAMESPACE_DNS, str(place_id))

    qdrant = get_qdrant()
    await qdrant.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=str(point_id),
                vector=vector,
                payload={
                    "place_id": str(place_id),
                    "summary": summary[:200],
                    **metadata,
                },
            )
        ],
    )
    return point_id


async def search_places(query: str, limit: int = 10) -> list[dict]:
    """자연어 쿼리로 유사 장소를 검색한다."""
    vector = await embed_text(query)
    qdrant = get_qdrant()
    results = await qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=vector,
        limit=limit,
        with_payload=True,
    )
    return [
        {"place_id": r.payload["place_id"], "score": r.score, **r.payload}
        for r in results
    ]
