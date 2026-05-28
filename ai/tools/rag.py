"""search_rag 툴 — FAISS 벡터 유사도 검색으로 장소 추천.

임베딩: Google text-embedding-004 (GOOGLE_API_KEY 필요)

인덱스 준비:
    python rag/seed.py   # rag/index.faiss + rag/metadata.json 생성
"""

import json
import os
from functools import lru_cache

import faiss
import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types
from langchain_core.tools import tool

from tools.logger import log_tool

load_dotenv()

EMBEDDING_MODEL = "text-embedding-004"
_RAG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rag")
_INDEX_PATH = os.path.join(_RAG_DIR, "index.faiss")
_META_PATH = os.path.join(_RAG_DIR, "metadata.json")


@lru_cache(maxsize=1)
def _load_index() -> faiss.Index:
    if not os.path.exists(_INDEX_PATH):
        raise FileNotFoundError(f"인덱스 없음: {_INDEX_PATH}\n'python rag/seed.py' 먼저 실행하세요.")
    return faiss.read_index(_INDEX_PATH)


@lru_cache(maxsize=1)
def _load_meta() -> tuple:
    if not os.path.exists(_META_PATH):
        raise FileNotFoundError(f"메타데이터 없음: {_META_PATH}")
    with open(_META_PATH, encoding="utf-8") as f:
        return tuple(json.load(f))


@lru_cache(maxsize=1)
def _get_client() -> genai.Client:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY 환경변수가 필요합니다.")
    return genai.Client(api_key=api_key)


def _embed_query(text: str) -> np.ndarray:
    client = _get_client()
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    vec = np.array([result.embeddings[0].values], dtype="float32")
    faiss.normalize_L2(vec)
    return vec


@tool
@log_tool
def search_rag(query: str, top_k: int = 5) -> str:
    """취향/분위기 설명을 받아 FAISS 벡터 검색으로 유사한 장소를 추천합니다.

    Args:
        query: 찾고 싶은 장소의 분위기나 특징 (예: "야경이 보이는 로맨틱한 저녁 데이트")
        top_k: 반환할 장소 수 (기본값 5)

    Returns:
        유사도 순서로 정렬된 장소 목록
    """
    try:
        index = _load_index()
        metadata = _load_meta()
        q_vec = _embed_query(query)
    except (FileNotFoundError, EnvironmentError) as e:
        return str(e)

    scores, ids = index.search(q_vec, min(top_k, index.ntotal))

    if ids[0][0] == -1:
        return "관련 장소를 찾을 수 없습니다."

    lines = [f"[search_rag] '{query}' 유사 장소 {len(ids[0])}개\n"]
    for score, idx in zip(scores[0], ids[0]):
        if idx == -1:
            break
        p = metadata[idx]
        tags = ", ".join(p.get("atmosphere_tags", []))
        lines.append(
            f"- {p['name']} ({p['area']}) / {p['category']}\n"
            f"  태그: {tags}\n"
            f"  {p['description']}\n"
            f"  유사도: {score:.3f}"
        )

    return "\n".join(lines)
