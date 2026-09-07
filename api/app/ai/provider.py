"""The single seam between WANAS and any language-model vendor.

Technical architecture, section 10, names dependency on one LLM provider as the
top technical risk and an abstraction layer as the mitigation. This module *is*
that layer: no other file in the codebase knows which vendor answers a question.

Two implementations ship:

* `ClaudeProvider`   — Anthropic Messages API, used when ANTHROPIC_API_KEY is set.
* `OfflineProvider`  — composes an answer strictly out of the retrieved heritage
                       passages. No network, no key, no invention. This is what a
                       competition jury sees in a room with no connectivity.

Both are held to the same contract: an answer may only assert what the passages
support, and every answer carries its sources.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import httpx

from app.config import settings

LANGUAGE_NAMES = {
    "ar": "Modern Standard Arabic",
    "dz": "Algerian Darija (الدارجة الجزائرية) — the everyday spoken register",
    "kab": "Tamazight (Kabyle)",
    "fr": "French",
    "en": "English",
}

RTL_LANGUAGES = {"ar", "dz"}

LEVEL_GUIDANCE = {
    "child": "Explain as you would to a curious ten-year-old: short sentences, "
             "one vivid image, no dates piled up.",
    "standard": "Explain to an interested adult visitor: concrete, warm, about "
                "120 words.",
    "expert": "Explain to someone who already knows the period: name the phases, "
              "the material evidence and what remains contested.",
}


@dataclass
class Passage:
    """One retrieved, editorially-validated fragment of the heritage corpus."""

    id: str
    title: str
    content: str
    source: str
    language: str
    score: float
    site_slug: str | None = None


@dataclass
class GuideAnswer:
    text: str
    sources: list[dict] = field(default_factory=list)
    provider: str = "offline"
    grounded: bool = True
    # True when retrieval found nothing solid and the guide declined to guess.
    refused: bool = False


class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def answer_guide(
        self,
        *,
        question: str,
        passages: list[Passage],
        language: str,
        level: str = "standard",
        history: list[dict] | None = None,
    ) -> GuideAnswer: ...

    @abstractmethod
    async def draft_product_story(
        self, *, product: str, craft: str, region: str, artisan: str, notes: str, language: str
    ) -> str: ...

    async def identify_site(
        self, *, image_b64: str, media_type: str, candidates: list[dict], language: str
    ) -> tuple[str | None, float, str]:
        """Return (site slug, confidence 0-1, note). Visual identification is
        optional capability: a provider that cannot see returns no match."""
        return None, 0.0, "visual-identification-unavailable"


# --------------------------------------------------------------------------- #
# Shared prompt construction
# --------------------------------------------------------------------------- #
GUIDE_SYSTEM = """You are WANAS (ونّاس), a warm travel companion for visitors in Algeria.

Absolute rules:
1. Answer ONLY from the numbered heritage passages provided. They are editorially
   validated; your own memory is not.
2. If the passages do not contain the answer, say plainly that you do not have
   that information and offer what you do have. Never fill a gap with a guess.
3. Cite the passages you used as [1], [2] inline.
4. Reply in {language_name} and in that language only.
5. {level_guidance}
6. Be a companion, not an encyclopaedia: one useful practical detail beats three
   dates. Never recommend alcohol, and respect prayer times and Ramadan hours
   when they are relevant to a visit.
"""


def build_context(passages: list[Passage]) -> str:
    blocks = []
    for i, p in enumerate(passages, 1):
        blocks.append(f"[{i}] {p.title} — source: {p.source}\n{p.content}")
    return "\n\n".join(blocks)


def sources_payload(passages: list[Passage]) -> list[dict]:
    return [
        {
            "ref": i,
            "id": p.id,
            "title": p.title,
            "source": p.source,
            "site_slug": p.site_slug,
            "score": round(p.score, 4),
        }
        for i, p in enumerate(passages, 1)
    ]


# --------------------------------------------------------------------------- #
# Claude
# --------------------------------------------------------------------------- #
class ClaudeProvider(LLMProvider):
    name = "claude"
    API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    async def _call(self, system: str, messages: list[dict], max_tokens: int) -> str:
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self._model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        }
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            response = await client.post(self.API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        return "".join(
            block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
        ).strip()

    async def answer_guide(
        self,
        *,
        question: str,
        passages: list[Passage],
        language: str,
        level: str = "standard",
        history: list[dict] | None = None,
    ) -> GuideAnswer:
        system = GUIDE_SYSTEM.format(
            language_name=LANGUAGE_NAMES.get(language, LANGUAGE_NAMES["fr"]),
            level_guidance=LEVEL_GUIDANCE.get(level, LEVEL_GUIDANCE["standard"]),
        )
        messages: list[dict] = []
        for turn in (history or [])[-6:]:
            messages.append({"role": turn["role"], "content": turn["content"]})
        messages.append(
            {
                "role": "user",
                "content": f"Heritage passages:\n\n{build_context(passages)}\n\n"
                f"Visitor question: {question}",
            }
        )
        text = await self._call(system, messages, settings.llm_max_tokens)
        return GuideAnswer(
            text=text,
            sources=sources_payload(passages),
            provider=self.name,
            grounded=True,
        )

    async def draft_product_story(
        self, *, product: str, craft: str, region: str, artisan: str, notes: str, language: str
    ) -> str:
        system = (
            "You write short origin stories for handmade Algerian craft objects, "
            "for a marketplace listing. Use only the facts the artisan supplied. "
            f"Write 70-100 words in {LANGUAGE_NAMES.get(language, 'French')}. "
            "Name the technique and the place. No invented history, no superlatives."
        )
        prompt = (
            f"Object: {product}\nCraft: {craft}\nRegion: {region}\n"
            f"Artisan: {artisan}\nArtisan's notes: {notes}"
        )
        return await self._call(system, [{"role": "user", "content": prompt}], 400)

    async def identify_site(
        self, *, image_b64: str, media_type: str, candidates: list[dict], language: str
    ) -> tuple[str | None, float, str]:
        listing = "\n".join(
            f"- {c['slug']}: {c['name']} ({c['region']}) — {c.get('category', '')}"
            for c in candidates
        )
        system = (
            "You identify Algerian heritage sites and craft objects from photographs. "
            "Choose only from the candidate list. Answer with exactly one line:\n"
            "SLUG|CONFIDENCE|SHORT_REASON\n"
            "where CONFIDENCE is a number between 0 and 1. If the photo matches none of "
            "the candidates, answer: none|0|not-in-list"
        )
        content = [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": image_b64},
            },
            {"type": "text", "text": f"Candidates:\n{listing}"},
        ]
        raw = await self._call(system, [{"role": "user", "content": content}], 120)
        parts = [p.strip() for p in raw.split("|")]
        if len(parts) < 2 or parts[0].lower() == "none":
            return None, 0.0, parts[-1] if parts else "no-match"
        try:
            confidence = max(0.0, min(float(parts[1]), 1.0))
        except ValueError:
            confidence = 0.5
        return parts[0], confidence, parts[2] if len(parts) > 2 else ""


# --------------------------------------------------------------------------- #
# Offline
# --------------------------------------------------------------------------- #
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?۔؟])\s+")

_LEAD_IN = {
    "fr": "Voici ce que dit la base patrimoniale WANAS :",
    "en": "Here is what the WANAS heritage base says:",
    "ar": "إليك ما تقوله قاعدة التراث في وناس:",
    "dz": "هاك واش كاين في قاعدة التراث تاع وناس:",
    "kab": "Atan wayen i d-yenna udlis n uzref n WANAS:",
}

_NO_ANSWER = {
    "fr": "Je n'ai pas cette information dans ma base patrimoniale vérifiée. "
          "Je préfère vous le dire plutôt que d'inventer. Reformulez, ou demandez-moi "
          "un site précis — Tipaza, Timgad, Djémila, la Casbah, le M'Zab, le Hoggar.",
    "en": "That is not in my verified heritage base. I would rather say so than invent it. "
          "Try rephrasing, or ask me about a specific site — Tipaza, Timgad, Djémila, "
          "the Casbah, the M'Zab or the Hoggar.",
    "ar": "لا أملك هذه المعلومة في قاعدة التراث الموثّقة لديّ، وأفضّل أن أخبرك بذلك بدل أن أختلق إجابة. "
          "أعد صياغة سؤالك أو اسألني عن موقع محدّد: تيبازة، تيمقاد، جميلة، القصبة، وادي ميزاب، الهقار.",
    "dz": "ما عنديش هاد المعلومة في قاعدة التراث المتأكّد منها، ونقولهالك خير ما نخترع. "
          "بدّل السؤال ولا سقسيني على بلاصة معيّنة: تيبازة، تيمقاد، جميلة، القصبة، ميزاب، الهقار.",
    "kab": "Ur sɛiɣ ara talɣut-a deg udlis-iw yettwaseglen. Steqsi-yi ɣef yiwen n wemkan: "
           "Tipaza, Timgad, Djemila, Lqasba, M'Zab, Hoggar.",
}

_FOOTER = {
    "fr": "Réponse composée hors ligne à partir des sources citées.",
    "en": "Answer composed offline from the cited sources.",
    "ar": "أُنشئت هذه الإجابة دون اتصال بالإنترنت انطلاقًا من المصادر المذكورة.",
    "dz": "هاد الجواب مبني بلا أنترنت من المصادر لي فوق.",
    "kab": "Tiririt tettwaheggza war internet seg yiɣbula yettwabedren.",
}


class OfflineProvider(LLMProvider):
    """Extractive, never generative. It can be wrong about emphasis, never about facts."""

    name = "offline"

    async def answer_guide(
        self,
        *,
        question: str,
        passages: list[Passage],
        language: str,
        level: str = "standard",
        history: list[dict] | None = None,
    ) -> GuideAnswer:
        if not passages:
            return GuideAnswer(
                text=_NO_ANSWER.get(language, _NO_ANSWER["fr"]),
                sources=[],
                provider=self.name,
                refused=True,
            )

        lead = _LEAD_IN.get(language, _LEAD_IN["fr"])
        budget = {"child": 1, "standard": 2, "expert": 4}.get(level, 2)

        parts: list[str] = []
        for i, passage in enumerate(passages[:3], 1):
            sentences = [s.strip() for s in _SENTENCE_SPLIT.split(passage.content) if s.strip()]
            picked = " ".join(sentences[:budget]) if sentences else passage.content
            parts.append(f"{picked} [{i}]")

        body = "\n\n".join(parts)
        footer = _FOOTER.get(language, _FOOTER["fr"])
        return GuideAnswer(
            text=f"{lead}\n\n{body}\n\n_{footer}_",
            sources=sources_payload(passages),
            provider=self.name,
            grounded=True,
        )

    async def draft_product_story(
        self, *, product: str, craft: str, region: str, artisan: str, notes: str, language: str
    ) -> str:
        templates = {
            "fr": "{product} — {craft} de {region}. Pièce réalisée par {artisan}. {notes}",
            "en": "{product} — {craft} from {region}. Made by {artisan}. {notes}",
            "ar": "{product} — {craft} من {region}. من صنع {artisan}. {notes}",
            "dz": "{product} — {craft} من {region}. خدمة {artisan}. {notes}",
            "kab": "{product} — {craft} seg {region}. Yexdem-it {artisan}. {notes}",
        }
        template = templates.get(language, templates["fr"])
        return template.format(
            product=product, craft=craft, region=region, artisan=artisan, notes=notes.strip()
        ).strip()


_provider: LLMProvider | None = None


def get_provider() -> LLMProvider:
    """Resolve the active provider once per process."""
    global _provider
    if _provider is None:
        if settings.llm_enabled:
            _provider = ClaudeProvider(settings.anthropic_api_key, settings.wanas_llm_model)
        else:
            _provider = OfflineProvider()
    return _provider


def reset_provider() -> None:
    """Test seam."""
    global _provider
    _provider = None
