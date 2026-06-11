from __future__ import annotations

import hashlib
import logging
import math
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Sequence

from env import load_project_env

load_project_env()

logger = logging.getLogger("ivory.vectorstore")

DEFAULT_COLLECTION_NAME = "ivory_knowledge_base"
DEFAULT_KB_DIR = Path(__file__).resolve().parents[1] / "knowledge_base"
DEFAULT_PERSIST_DIR = Path(
    os.getenv("CHROMA_PERSIST_DIR", str(Path(__file__).resolve().parents[1] / "vectorstore"))
)
DEFAULT_EMBEDDING_MODEL = os.getenv(
    "IVORY_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
MAX_CHUNK_CHARS = 1200
EMBEDDING_DIMENSION = 256


@dataclass(slots=True)
class KnowledgeDocument:
    source: str
    title: str
    content: str


@dataclass(slots=True)
class KnowledgeChunk:
    id: str
    source: str
    title: str
    content: str
    chunk_index: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RetrievedChunk:
    id: str
    score: float
    source: str
    title: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class IngestionReport:
    document_count: int
    chunk_count: int
    backend: str
    collection_name: str
    persist_dir: str


@dataclass(slots=True)
class KnowledgeBaseIndex:
    backend: str
    chunks: list[KnowledgeChunk]
    embeddings: list[list[float]]
    persist_dir: Path
    collection_name: str
    chroma_collection: Any | None = None

    def query(self, query_text: str, top_k: int = 4) -> list[RetrievedChunk]:
        query_embedding = _embed_texts([query_text])[0]
        if self.backend == "chroma" and self.chroma_collection is not None:
            return _query_chroma(self.chroma_collection, query_text, query_embedding, top_k)
        return _query_in_memory(self.chunks, self.embeddings, query_text, query_embedding, top_k)


class _SentenceTransformerBackend:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = None
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore

            self._model = SentenceTransformer(model_name)
            logger.info("sentence-transformers loaded: %s", model_name)
        except Exception as exc:
            logger.warning(
                "sentence-transformers unavailable (%s) — falling back to hash embeddings. "
                "Install with: pip install sentence-transformers",
                exc,
            )
            self._model = None

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        if self._model is not None:
            try:
                vectors = self._model.encode(list(texts), normalize_embeddings=True)
                if hasattr(vectors, "tolist"):
                    return [list(map(float, row)) for row in vectors.tolist()]
                return [list(map(float, row)) for row in vectors]
            except Exception:
                pass
        return [_hash_embedding(text) for text in texts]


class _HashEmbeddingBackend:
    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        return [_hash_embedding(text) for text in texts]


_INDEX_CACHE: dict[tuple[str, str, str], KnowledgeBaseIndex] = {}


def get_knowledge_base_dir() -> Path:
    return DEFAULT_KB_DIR


def get_persist_dir() -> Path:
    return DEFAULT_PERSIST_DIR


def load_knowledge_documents(kb_dir: str | Path | None = None) -> list[KnowledgeDocument]:
    base_dir = Path(kb_dir) if kb_dir is not None else get_knowledge_base_dir()
    documents: list[KnowledgeDocument] = []
    for path in sorted(base_dir.glob("*.md")):
        content = path.read_text(encoding="utf-8").strip()
        documents.append(
            KnowledgeDocument(
                source=path.name,
                title=_extract_title(content, path.stem),
                content=content,
            )
        )
    return documents


def chunk_documents(documents: Sequence[KnowledgeDocument]) -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    for document in documents:
        chunks.extend(_chunk_document(document))
    return chunks


def ingest_knowledge_base(
    kb_dir: str | Path | None = None,
    persist_dir: str | Path | None = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> IngestionReport:
    index = ensure_knowledge_base_index(
        kb_dir=kb_dir,
        persist_dir=persist_dir,
        collection_name=collection_name,
    )
    return IngestionReport(
        document_count=len(load_knowledge_documents(kb_dir)),
        chunk_count=len(index.chunks),
        backend=index.backend,
        collection_name=collection_name,
        persist_dir=str(index.persist_dir),
    )


def search_knowledge_base(
    query: str,
    *,
    top_k: int = 4,
    kb_dir: str | Path | None = None,
    persist_dir: str | Path | None = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> list[RetrievedChunk]:
    index = ensure_knowledge_base_index(
        kb_dir=kb_dir,
        persist_dir=persist_dir,
        collection_name=collection_name,
    )
    return index.query(query, top_k=top_k)


def ensure_knowledge_base_index(
    *,
    kb_dir: str | Path | None = None,
    persist_dir: str | Path | None = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> KnowledgeBaseIndex:
    kb_path = Path(kb_dir) if kb_dir is not None else get_knowledge_base_dir()
    persist_path = Path(persist_dir) if persist_dir is not None else get_persist_dir()
    cache_key = (str(kb_path.resolve()), str(persist_path.resolve()), collection_name)

    cached = _INDEX_CACHE.get(cache_key)
    if cached is not None:
        return cached

    documents = load_knowledge_documents(kb_path)
    logger.info("Loaded %d documents from %s", len(documents), kb_path)
    chunks = chunk_documents(documents)
    logger.info("Split into %d chunks", len(chunks))
    embeddings = _embed_texts([chunk.content for chunk in chunks])
    backend_name = _embedding_backend(DEFAULT_EMBEDDING_MODEL).__class__.__name__
    logger.info("Embeddings generated via %s (dim=%d)", backend_name, len(embeddings[0]) if embeddings else 0)
    chroma_collection = _maybe_build_chroma_collection(
        chunks=chunks,
        embeddings=embeddings,
        persist_path=persist_path,
        collection_name=collection_name,
    )
    index = KnowledgeBaseIndex(
        backend="chroma" if chroma_collection is not None else "memory",
        chunks=chunks,
        embeddings=embeddings,
        persist_dir=persist_path,
        collection_name=collection_name,
        chroma_collection=chroma_collection,
    )
    logger.info("Index ready — backend=%s chunks=%d", index.backend, len(chunks))
    _INDEX_CACHE[cache_key] = index
    return index


def _maybe_build_chroma_collection(
    *,
    chunks: Sequence[KnowledgeChunk],
    embeddings: Sequence[Sequence[float]],
    persist_path: Path,
    collection_name: str,
) -> Any | None:
    try:
        import chromadb  # type: ignore
    except Exception:
        return None

    persist_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_path))
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    if chunks:
        try:
            collection.upsert(
                ids=[chunk.id for chunk in chunks],
                documents=[chunk.content for chunk in chunks],
                metadatas=[dict(chunk.metadata) for chunk in chunks],
                embeddings=[list(map(float, embedding)) for embedding in embeddings],
            )
        except Exception as exc:
            if "dimension" in str(exc).lower():
                logger.warning(
                    "ChromaDB dimension mismatch (%s) — deleting stale collection and rebuilding",
                    exc,
                )
                client.delete_collection(collection_name)
                collection = client.create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
                collection.upsert(
                    ids=[chunk.id for chunk in chunks],
                    documents=[chunk.content for chunk in chunks],
                    metadatas=[dict(chunk.metadata) for chunk in chunks],
                    embeddings=[list(map(float, embedding)) for embedding in embeddings],
                )
                logger.info("ChromaDB collection rebuilt with correct embedding dimension")
            else:
                raise
    return collection


def _query_chroma(
    collection: Any,
    query_text: str,
    query_embedding: Sequence[float],
    top_k: int,
) -> list[RetrievedChunk]:
    try:
        results = collection.query(
            query_embeddings=[list(map(float, query_embedding))],
            n_results=max(6, top_k * 3),
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:
        if "dimension" in str(exc).lower():
            raise RuntimeError(
                f"ChromaDB dimension mismatch during query: {exc}. "
                "The vectorstore was built with a different embedding model. "
                "Restart the backend to trigger automatic collection rebuild."
            ) from exc
        raise

    documents = _flatten_first_result(results.get("documents"))
    metadatas = _flatten_first_result(results.get("metadatas"))
    distances = _flatten_first_result(results.get("distances"))
    ids = _flatten_first_result(results.get("ids"))
    combined = _combine_results(ids, documents, metadatas, distances, top_k=max(6, top_k * 3), invert_distance=True)
    return _rerank_results(query_text, combined, top_k)


def _query_in_memory(
    chunks: Sequence[KnowledgeChunk],
    embeddings: Sequence[Sequence[float]],
    query_text: str,
    query_embedding: Sequence[float],
    top_k: int,
) -> list[RetrievedChunk]:
    scored: list[tuple[float, KnowledgeChunk]] = []
    for chunk, embedding in zip(chunks, embeddings):
        scored.append((_cosine_similarity(query_embedding, embedding), chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    results = [
        RetrievedChunk(
            id=chunk.id,
            score=score,
            source=chunk.source,
            title=chunk.title,
            content=chunk.content,
            metadata=dict(chunk.metadata),
        )
        for score, chunk in scored[: max(6, top_k * 3)]
    ]
    return _rerank_results(query_text, results, top_k)


def _combine_results(
    ids: Sequence[Any] | None,
    documents: Sequence[Any] | None,
    metadatas: Sequence[Any] | None,
    distances: Sequence[Any] | None,
    *,
    top_k: int,
    invert_distance: bool = False,
) -> list[RetrievedChunk]:
    id_values = list(ids or [])
    document_values = list(documents or [])
    metadata_values = list(metadatas or [])
    distance_values = list(distances or [])
    results: list[RetrievedChunk] = []

    for index, document in enumerate(document_values[: max(1, top_k)]):
        metadata = metadata_values[index] if index < len(metadata_values) and isinstance(metadata_values[index], dict) else {}
        raw_distance = distance_values[index] if index < len(distance_values) else None
        score = 0.0
        if isinstance(raw_distance, (int, float)):
            score = 1.0 - float(raw_distance) if invert_distance else float(raw_distance)
        results.append(
            RetrievedChunk(
                id=str(id_values[index]) if index < len(id_values) else f"chunk-{index}",
                score=score,
                source=str(metadata.get("source", "")),
                title=str(metadata.get("title", "")),
                content=str(document),
                metadata=dict(metadata),
            )
        )
    return results


def _rerank_results(
    query_text: str,
    results: Sequence[RetrievedChunk],
    top_k: int,
) -> list[RetrievedChunk]:
    query_tokens = set(_tokenize_text(query_text))
    if not query_tokens:
        return list(results[: max(1, top_k)])

    reranked: list[tuple[float, RetrievedChunk]] = []
    for result in results:
        title_tokens = set(_tokenize_text(result.title))
        source_tokens = set(_tokenize_text(result.source))
        content_tokens = set(_tokenize_text(result.content[:800]))

        title_overlap = len(query_tokens & title_tokens)
        source_overlap = len(query_tokens & source_tokens)
        content_overlap = len(query_tokens & content_tokens)

        score = float(result.score)
        score += title_overlap * 0.35
        score += source_overlap * 0.2
        score += min(content_overlap, 8) * 0.08

        if "offer" in query_tokens and "insurance" in query_tokens:
            if {"auto", "home", "life"} & content_tokens:
                score += 0.35

        reranked.append((score, result))

    reranked.sort(key=lambda item: item[0], reverse=True)
    return [result for _, result in reranked[: max(1, top_k)]]


@lru_cache(maxsize=2)
def _embedding_backend(model_name: str = DEFAULT_EMBEDDING_MODEL) -> Any:
    backend = _SentenceTransformerBackend(model_name)
    if getattr(backend, "_model", None) is not None:
        return backend
    return _HashEmbeddingBackend()


def _embed_texts(texts: Sequence[str]) -> list[list[float]]:
    backend = _embedding_backend(DEFAULT_EMBEDDING_MODEL)
    return [list(map(float, vector)) for vector in backend.encode(list(texts))]


def _chunk_document(document: KnowledgeDocument) -> list[KnowledgeChunk]:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", document.content) if paragraph.strip()]
    chunks: list[KnowledgeChunk] = []
    buffer: list[str] = []
    chunk_index = 0
    buffer_len = 0

    for paragraph in paragraphs:
        if buffer and buffer_len + len(paragraph) > MAX_CHUNK_CHARS:
            chunks.append(_make_chunk(document, chunk_index, buffer))
            chunk_index += 1
            buffer = []
            buffer_len = 0
        buffer.append(paragraph)
        buffer_len = len("\n\n".join(buffer))

    if buffer:
        chunks.append(_make_chunk(document, chunk_index, buffer))
    return chunks


def _make_chunk(document: KnowledgeDocument, chunk_index: int, paragraphs: Sequence[str]) -> KnowledgeChunk:
    content = "\n\n".join(paragraphs).strip()
    return KnowledgeChunk(
        id=f"{Path(document.source).stem}-{chunk_index}",
        source=document.source,
        title=document.title,
        content=content,
        chunk_index=chunk_index,
        metadata={
            "source": document.source,
            "title": document.title,
            "chunk_index": chunk_index,
        },
    )


def _extract_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            if title:
                return title
    return fallback


def _hash_embedding(text: str) -> list[float]:
    tokens = _tokenize_text(text)
    vector = [0.0] * EMBEDDING_DIMENSION
    if not tokens:
        return vector
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        vector[digest[0] % EMBEDDING_DIMENSION] += 1.0
    return _normalize(vector)


def _normalize(vector: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if not norm:
        return list(vector)
    return [value / norm for value in vector]


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        return 0.0
    return sum(float(a) * float(b) for a, b in zip(left, right))


def _flatten_first_result(value: Any) -> list[Any]:
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, list):
            return list(first)
        return list(value)
    return []


def _tokenize_text(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())
