"""Retrieval-Augmented Generation over the Algerian heritage corpus.

Architecture section 5: index offline, retrieve at query time, ground the answer.

Retrieval is hybrid. A dense pass over pgvector catches paraphrase and
misspelling; a lexical pass over Postgres full-text catches proper nouns the
dense pass dilutes — "Tin Hinan", "Beni Hammad" — and the two are fused. Either
half alone would let a wrong site through on a name the other one knows.

Nothing below the relevance floor reaches the language model: an empty passage
list is a refusal, not a prompt (AC-1.2).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.ai.embeddings import get_embedder, normalize
from app.ai.provider import Passage
from app.config import settings

# Weights over the two retrieval channels. Dense leads; lexical breaks ties and
# rescues exact proper nouns.
DENSE_WEIGHT = 0.55
LEXICAL_WEIGHT = 0.45
# ts_rank returns roughly 0.0-0.1 for ordinary matches; scale it onto [0, 1].
TS_RANK_SCALE = 10.0
# A chunk written in the language the visitor is speaking is worth a nudge.
SAME_LANGUAGE_BOOST = 1.15
# Darija and MSA share a script and most vocabulary; treat them as one family.
LANGUAGE_FAMILY = {"ar": "ar", "dz": "ar", "fr": "fr", "en": "en", "kab": "kab"}


@dataclass
class ScoredChunk:
    id: str
    title: str
    content: str
    source: str
    language: str
    site_slug: str | None
    dense: float
    lexical: float
    fused: float


def fuse(dense: float, lexical: float, *, same_language: bool = False) -> float:
    """Combine the two retrieval channels into one comparable score.

    Kept pure and separate from the SQL so the ranking rule can be tested
    without a database.
    """
    lexical_norm = min(max(lexical, 0.0) * TS_RANK_SCALE, 1.0)
    score = DENSE_WEIGHT * max(dense, 0.0) + LEXICAL_WEIGHT * lexical_norm
    if same_language:
        score *= SAME_LANGUAGE_BOOST
    return score


def chunk_document(
    content: str, *, target_chars: int = 700, overlap_chars: int = 120
) -> list[str]:
    """Split a heritage document on paragraph then sentence boundaries.

    Chunks that straddle a topic boundary retrieve badly, so paragraphs are
    never merged across a blank line unless the result stays under target.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", content) if p.strip()]
    chunks: list[str] = []
    buffer = ""

    for paragraph in paragraphs:
        if len(paragraph) > target_chars:
            if buffer:
                chunks.append(buffer)
                buffer = ""
            sentences = re.split(r"(?<=[.!?۔؟])\s+", paragraph)
            current = ""
            for sentence in sentences:
                if current and len(current) + len(sentence) + 1 > target_chars:
                    chunks.append(current.strip())
                    tail = current[-overlap_chars:] if overlap_chars else ""
                    current = f"{tail} {sentence}".strip()
                else:
                    current = f"{current} {sentence}".strip()
            if current:
                chunks.append(current.strip())
        elif len(buffer) + len(paragraph) + 2 <= target_chars:
            buffer = f"{buffer}\n\n{paragraph}".strip()
        else:
            chunks.append(buffer)
            buffer = paragraph

    if buffer:
        chunks.append(buffer)
    return [c for c in chunks if c]


class HeritageRetriever:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.embedder = get_embedder()

    def _dense(self, query: str, limit: int) -> dict[str, tuple]:
        vector = self.embedder.embed(query)
        if not any(vector):
            return {}
        rows = self.db.execute(
            sql_text(
                """
                SELECT c.id, c.title, c.content, c.source, c.language, s.slug AS site_slug,
                       1 - (c.embedding <=> CAST(:vec AS vector)) AS dense
                FROM heritage_chunks c
                LEFT JOIN tourist_sites s ON s.id = c.site_id
                WHERE c.validated IS TRUE AND c.embedding IS NOT NULL
                ORDER BY c.embedding <=> CAST(:vec AS vector)
                LIMIT :limit
                """
            ),
            {"vec": str(vector), "limit": limit},
        ).mappings()
        return {r["id"]: r for r in rows}

    def _lexical(self, query: str, limit: int) -> dict[str, tuple]:
        folded = normalize(query)
        rows = self.db.execute(
            sql_text(
                """
                SELECT c.id, c.title, c.content, c.source, c.language, s.slug AS site_slug,
                       ts_rank(to_tsvector('simple', c.search_text),
                               plainto_tsquery('simple', :q)) AS lexical
                FROM heritage_chunks c
                LEFT JOIN tourist_sites s ON s.id = c.site_id
                WHERE c.validated IS TRUE
                  AND to_tsvector('simple', c.search_text) @@ plainto_tsquery('simple', :q)
                ORDER BY lexical DESC
                LIMIT :limit
                """
            ),
            {"q": folded, "limit": limit},
        ).mappings()
        return {r["id"]: r for r in rows}

    def retrieve(self, query: str, *, language: str = "fr", top_k: int | None = None) -> list[Passage]:
        top_k = top_k or settings.retrieval_top_k
        pool = max(top_k * 4, 20)

        dense_rows = self._dense(query, pool)
        lexical_rows = self._lexical(query, pool)

        family = LANGUAGE_FAMILY.get(language, language)
        merged: dict[str, ScoredChunk] = {}
        for chunk_id in set(dense_rows) | set(lexical_rows):
            row = dense_rows.get(chunk_id) or lexical_rows.get(chunk_id)
            dense = float(dense_rows.get(chunk_id, {}).get("dense", 0.0) or 0.0)
            lexical = float(lexical_rows.get(chunk_id, {}).get("lexical", 0.0) or 0.0)
            same_language = LANGUAGE_FAMILY.get(row["language"], row["language"]) == family
            merged[chunk_id] = ScoredChunk(
                id=row["id"],
                title=row["title"],
                content=row["content"],
                source=row["source"],
                language=row["language"],
                site_slug=row["site_slug"],
                dense=dense,
                lexical=lexical,
                fused=fuse(dense, lexical, same_language=same_language),
            )

        ranked = sorted(merged.values(), key=lambda c: c.fused, reverse=True)
        kept = [c for c in ranked if c.fused >= settings.relevance_floor][:top_k]

        return [
            Passage(
                id=c.id,
                title=c.title,
                content=c.content,
                source=c.source,
                language=c.language,
                score=c.fused,
                site_slug=c.site_slug,
            )
            for c in kept
        ]
