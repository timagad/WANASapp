"""Hybrid recommendation engine.

Architecture section 5.3: collaborative filtering blended with content-based
filtering, specifically to blunt cold start. Both halves are pure functions over
plain dictionaries so the ranking rules can be tested without a database — the
class at the bottom is the only part that touches SQL.

Cold start is not a special case bolted on: the blend weight is a function of
how much evidence the user has actually produced, so a first-session visitor is
served by content alone and drifts toward collaborative as they interact.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import InteractionEvent, Review, TouristSite

# Signals worth different amounts of evidence.
EVENT_WEIGHTS = {"view": 0.25, "save": 0.7, "ar_open": 0.6, "book": 1.0}
# Below this much evidence, collaborative filtering is noise: stay content-only.
COLD_START_EVIDENCE = 3.0
# Ceiling on the collaborative share, so a popular-item echo chamber cannot form.
MAX_COLLABORATIVE_SHARE = 0.6


@dataclass
class Scored:
    site_id: str
    score: float
    content: float
    collaborative: float
    reason: str


def blend_weight(evidence: float) -> float:
    """Share of the final score given to collaborative filtering.

    0.0 for a brand-new visitor, rising smoothly with accumulated evidence and
    capped so content signals always retain a voice.
    """
    if evidence <= 0:
        return 0.0
    ramp = min(evidence / (COLD_START_EVIDENCE * 2.0), 1.0)
    return MAX_COLLABORATIVE_SHARE * ramp


def content_score(
    interests: dict[str, float],
    tags: list[str],
    *,
    popularity: float = 0.5,
    region_match: bool = False,
) -> float:
    """How well a site matches a stated interest profile.

    Interest overlap dominates; popularity is only a tie-breaker, so a niche
    site the visitor actually asked for outranks a famous one they did not.
    """
    if tags:
        matched = sum(max(interests.get(tag, 0.0), 0.0) for tag in tags)
        # Normalise by sqrt so a site tagged with everything cannot win by breadth.
        overlap = matched / math.sqrt(len(tags))
    else:
        overlap = 0.0
    score = 0.72 * overlap + 0.18 * popularity
    if region_match:
        score += 0.10
    return score


def build_cooccurrence(user_items: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    """Item-item similarity from co-interaction, cosine-normalised.

    `user_items` maps user id -> {site id: evidence weight}.
    """
    dot: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    norm: dict[str, float] = defaultdict(float)

    for items in user_items.values():
        entries = list(items.items())
        for site_id, weight in entries:
            norm[site_id] += weight * weight
        for i, (a, wa) in enumerate(entries):
            for b, wb in entries[i + 1 :]:
                dot[a][b] += wa * wb
                dot[b][a] += wa * wb

    similarity: dict[str, dict[str, float]] = {}
    for a, neighbours in dot.items():
        na = math.sqrt(norm[a]) or 1.0
        similarity[a] = {
            b: value / (na * (math.sqrt(norm[b]) or 1.0)) for b, value in neighbours.items()
        }
    return similarity


def collaborative_score(
    candidate: str, profile: dict[str, float], similarity: dict[str, dict[str, float]]
) -> float:
    """Score a candidate by its similarity to what this user already engaged with."""
    if not profile:
        return 0.0
    total = 0.0
    weight_sum = 0.0
    for liked, weight in profile.items():
        sim = similarity.get(liked, {}).get(candidate, 0.0)
        total += sim * weight
        weight_sum += weight
    return total / weight_sum if weight_sum else 0.0


def rank(
    candidates: list[dict],
    *,
    interests: dict[str, float],
    profile: dict[str, float],
    similarity: dict[str, dict[str, float]],
    home_region: str | None = None,
    exclude: set[str] | None = None,
    limit: int = 10,
) -> list[Scored]:
    """Blend both channels and order the result.

    `candidates` are dicts with id, tags, popularity, region.
    """
    exclude = exclude or set()
    evidence = sum(profile.values())
    beta = blend_weight(evidence)

    scored: list[Scored] = []
    for site in candidates:
        if site["id"] in exclude or site["id"] in profile:
            continue
        content = content_score(
            interests,
            site.get("tags") or [],
            popularity=site.get("popularity", 0.5),
            # Visitors are here to leave their own province, so a match with the
            # home region is a mild negative, not a positive.
            region_match=False,
        )
        if home_region and site.get("region") == home_region:
            content *= 0.85
        collab = collaborative_score(site["id"], profile, similarity)
        total = (1 - beta) * content + beta * collab
        reason = "similar-visitors" if beta > 0 and collab > content else "your-interests"
        scored.append(
            Scored(
                site_id=site["id"],
                score=total,
                content=content,
                collaborative=collab,
                reason=reason,
            )
        )

    scored.sort(key=lambda s: s.score, reverse=True)
    return scored[:limit]


class Recommender:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _profiles(self) -> dict[str, dict[str, float]]:
        """Everyone's evidence, used to derive item-item similarity."""
        profiles: dict[str, dict[str, float]] = defaultdict(dict)

        events = self.db.execute(
            select(InteractionEvent.user_id, InteractionEvent.site_id, InteractionEvent.kind).where(
                InteractionEvent.user_id.is_not(None), InteractionEvent.site_id.is_not(None)
            )
        ).all()
        for user_id, site_id, kind in events:
            weight = EVENT_WEIGHTS.get(kind, 0.2)
            profiles[user_id][site_id] = max(profiles[user_id].get(site_id, 0.0), weight)

        reviews = self.db.execute(
            select(Review.user_id, Review.site_id, Review.rating).where(Review.site_id.is_not(None))
        ).all()
        for user_id, site_id, rating in reviews:
            # A 5 is strong evidence, a 1 is evidence of the opposite; centre on 3.
            weight = (rating - 3) / 2.0
            if weight > 0:
                profiles[user_id][site_id] = max(profiles[user_id].get(site_id, 0.0), weight)

        return profiles

    def for_user(
        self,
        *,
        user_id: str | None,
        interests: dict[str, float],
        home_region: str | None = None,
        exclude: set[str] | None = None,
        limit: int = 10,
    ) -> list[tuple[TouristSite, Scored]]:
        sites = self.db.execute(select(TouristSite)).scalars().all()
        candidates = [
            {
                "id": s.id,
                "tags": list(s.tags or []),
                "popularity": s.popularity,
                "region": s.region,
            }
            for s in sites
        ]

        profiles = self._profiles()
        similarity = build_cooccurrence(profiles)
        profile = profiles.get(user_id, {}) if user_id else {}

        ranked = rank(
            candidates,
            interests=interests,
            profile=profile,
            similarity=similarity,
            home_region=home_region,
            exclude=exclude,
            limit=limit,
        )
        by_id = {s.id: s for s in sites}
        return [(by_id[r.site_id], r) for r in ranked if r.site_id in by_id]
