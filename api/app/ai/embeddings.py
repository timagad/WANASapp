"""Embeddings for the heritage corpus.

The default embedder is deterministic, local and dependency-free: a signed
hashing projection over word tokens and character n-grams. That matters for two
reasons the dossier is explicit about — the platform has to demo with no network
(NFR-6), and no per-call embedding cost may sit between an artisan and their
listing (NFR-7).

A hashed bag-of-n-grams is lexical, not semantic. The retriever compensates by
fusing these vectors with Postgres full-text search rather than trusting either
alone. Swapping in a neural embedder later means implementing `Embedder` and
re-running `python -m app.seed --reindex`; nothing else moves.
"""
from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from abc import ABC, abstractmethod
from collections import Counter

from app.config import settings

# Arabic diacritics (tashkeel) and the tatweel elongation mark.
_ARABIC_MARKS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_ALEF = re.compile(r"[آأإٱ]")
_TOKEN = re.compile(r"[\w؀-ۿⴰ-⵿]+", re.UNICODE)

# Words carrying no retrieval signal in any of the five supported languages.
# The Darija block matters more than it looks: a spoken-register question is
# mostly function words, so leaving them in buries the one word that carries the
# topic. Written unvowelled, so they match post-normalisation.
_STOPWORDS = {
    "le", "la", "les", "de", "des", "du", "un", "une", "et", "en", "au", "aux",
    "ce", "cette", "qui", "que", "est", "sont", "dans", "sur", "pour", "avec",
    "the", "of", "a", "an", "and", "in", "to", "is", "are", "for", "on", "with",
    "what", "where", "there", "it", "its", "this", "that",
    # Modern Standard Arabic
    "من", "في", "علي", "الي", "عن", "هو", "هي", "ما", "هذا", "هذه", "التي", "الذي",
    "كان", "كانت", "قد", "لقد", "ثم", "او", "ايضا", "بين", "عند", "الي",
    # Algerian Darija
    "واش", "كيفاش", "بزاف", "نتاع", "تاع", "راه", "راهي", "كي", "وين", "كاين",
    "كاينه", "فيها", "فيه", "هاد", "هادي", "هاذ", "شحال", "قداش", "علاش", "باش",
    "نحب", "تحب", "نروح", "غير", "برك", "مليح", "شويه",
}

# A leading conjunction fuses onto the next word in Arabic script, so "وواش" is
# "و" + "واش". Strip it when what remains is itself a stopword.
_ARABIC_PREFIXES = ("و", "ف")


def normalize(text: str) -> str:
    """Fold a string into the form both the embedder and the lexical index see."""
    text = unicodedata.normalize("NFKC", text).lower()
    text = _ARABIC_MARKS.sub("", text)
    text = _ALEF.sub("ا", text)          # أ إ آ ٱ -> ا
    text = text.replace("ى", "ي")   # ى -> ي
    text = text.replace("ئ", "ي")   # ئ -> ي
    text = text.replace("ؤ", "و")   # ؤ -> و
    text = text.replace("ة", "ه")   # ة -> ه
    return text


def _is_stopword(token: str) -> bool:
    if token in _STOPWORDS:
        return True
    return any(
        token.startswith(prefix) and token[len(prefix) :] in _STOPWORDS
        for prefix in _ARABIC_PREFIXES
    )


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(normalize(text)) if not _is_stopword(t)]


def script_of(token: str) -> str:
    """Which writing system a token belongs to.

    Features are namespaced by script so an Arabic trigram can never collide
    with a Latin one. Without this, a hashed vector lets an Arabic question
    match a French passage on pure hash noise — which it did, and which no
    amount of tuning the weights would have fixed.
    """
    for character in token:
        code = ord(character)
        if 0x0600 <= code <= 0x06FF or 0x0750 <= code <= 0x077F:
            return "ar"
        if 0x2D30 <= code <= 0x2D7F:
            return "tfng"
    return "la"


def _char_ngrams(token: str, n: int = 3) -> list[str]:
    """Character n-grams make the embedder robust to Darija's loose spelling."""
    if len(token) <= n:
        return [token]
    padded = f"^{token}$"
    return [padded[i : i + n] for i in range(len(padded) - n + 1)]


def _bucket(feature: str, dim: int) -> tuple[int, float]:
    """Map a feature to a bucket and a sign, so collisions cancel instead of pile up."""
    digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
    value = int.from_bytes(digest, "big")
    return value % dim, 1.0 if (value >> 63) & 1 else -1.0


class Embedder(ABC):
    """The seam a neural embedding provider would slot into."""

    dim: int

    @abstractmethod
    def embed(self, text: str) -> list[float]: ...

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


class HashingEmbedder(Embedder):
    """Signed hashing projection of word tokens + character trigrams."""

    def __init__(self, dim: int | None = None, ngram_weight: float = 0.45) -> None:
        self.dim = dim or settings.embedding_dim
        self.ngram_weight = ngram_weight

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        tokens = tokenize(text)
        if not tokens:
            return vector

        counts = Counter(tokens)
        for token, count in counts.items():
            # Sublinear term frequency: the tenth mention of "Tipaza" is not
            # ten times the evidence of the first.
            weight = 1.0 + math.log(count)
            script = script_of(token)
            index, sign = _bucket(f"w:{script}:{token}", self.dim)
            vector[index] += sign * weight
            for gram in _char_ngrams(token):
                gi, gs = _bucket(f"c:{script}:{gram}", self.dim)
                vector[gi] += gs * weight * self.ngram_weight

        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0.0:
            return vector
        return [v / norm for v in vector]


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity for already-normalised vectors, defensive about zeros."""
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = HashingEmbedder()
    return _embedder
