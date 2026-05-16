from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams

from app.core.config import settings

COLLECTION_NAME = "place_summaries"
VECTOR_SIZE = 1536  # text-embedding-3-small 기준

_client: AsyncQdrantClient | None = None


def get_qdrant() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
        )
    return _client


async def ensure_collection() -> None:
    client = get_qdrant()
    existing = await client.get_collections()
    names = [c.name for c in existing.collections]
    if COLLECTION_NAME not in names:
        await client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
