"""Photograph a monument, get its story.

Two identification channels, deliberately ranked in that order:

1. **Where the photo was taken.** A JPEG shot at Tipaza carries Tipaza's
   coordinates in its EXIF. That is not a guess, it is a measurement, and it
   works with no model and no network. The client may also pass a live fix.
2. **What the photo shows.** Only a multimodal model can do this, so it runs
   when one is configured and refines or overrides the geographic shortlist.

When neither channel is confident, the endpoint says so and offers the nearby
candidates rather than naming a monument it cannot see (NFR-5).
"""
from __future__ import annotations

import base64
import io
from dataclasses import dataclass

from app.ai.planner import haversine_km
from app.ai.provider import LLMProvider

# Beyond this, "you are standing at it" stops being a reasonable inference.
GEO_CONFIDENT_KM = 0.6
GEO_PLAUSIBLE_KM = 8.0
# Below this the API reports "unidentified" rather than naming a site.
MIN_REPORTABLE_CONFIDENCE = 0.35


@dataclass
class Identification:
    site_slug: str | None
    confidence: float
    method: str
    candidates: list[dict]


def extract_gps(image_bytes: bytes) -> tuple[float, float] | None:
    """Pull a decimal (lat, lon) out of EXIF, or None if the photo has no fix."""
    try:
        from PIL import Image, ExifTags
    except ImportError:  # pragma: no cover - Pillow is a hard dependency in prod
        return None

    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            exif = image.getexif()
            if not exif:
                return None
            gps_tag = next(
                (tag for tag, name in ExifTags.TAGS.items() if name == "GPSInfo"), None
            )
            gps = exif.get_ifd(gps_tag) if gps_tag else None
            if not gps:
                return None

            def to_degrees(values) -> float:
                d, m, s = (float(v) for v in values)
                return d + m / 60.0 + s / 3600.0

            lat = to_degrees(gps[2])
            if str(gps.get(1, "N")).upper().startswith("S"):
                lat = -lat
            lon = to_degrees(gps[4])
            if str(gps.get(3, "E")).upper().startswith("W"):
                lon = -lon
            return lat, lon
    except (KeyError, ValueError, TypeError, OSError):
        return None


def geographic_candidates(
    sites: list[dict], point: tuple[float, float], *, limit: int = 5
) -> list[dict]:
    """Rank sites by distance from a fix, attaching a distance-derived confidence."""
    scored = []
    for site in sites:
        distance = haversine_km(point, (site["latitude"], site["longitude"]))
        if distance <= GEO_CONFIDENT_KM:
            confidence = 0.92
        elif distance <= GEO_PLAUSIBLE_KM:
            # Decay linearly across the plausible band.
            span = GEO_PLAUSIBLE_KM - GEO_CONFIDENT_KM
            confidence = 0.92 - 0.55 * ((distance - GEO_CONFIDENT_KM) / span)
        else:
            confidence = 0.0
        scored.append({**site, "distance_km": round(distance, 2), "confidence": round(confidence, 3)})
    scored.sort(key=lambda s: s["distance_km"])
    return scored[:limit]


async def identify(
    *,
    image_bytes: bytes,
    media_type: str,
    sites: list[dict],
    provider: LLMProvider,
    language: str = "fr",
    fix: tuple[float, float] | None = None,
) -> Identification:
    point = fix or extract_gps(image_bytes)
    candidates = geographic_candidates(sites, point) if point else []

    # Give the vision model the geographic shortlist when we have one; the whole
    # catalogue otherwise. A shortlist both cuts tokens and cuts wrong answers.
    shortlist = candidates or sites[:25]
    slug, confidence, note = await provider.identify_site(
        image_b64=base64.b64encode(image_bytes).decode("ascii"),
        media_type=media_type,
        candidates=shortlist,
        language=language,
    )

    if slug and confidence >= MIN_REPORTABLE_CONFIDENCE:
        return Identification(slug, confidence, "visual", candidates)

    if candidates and candidates[0]["confidence"] >= MIN_REPORTABLE_CONFIDENCE:
        top = candidates[0]
        return Identification(top["slug"], top["confidence"], "geolocation", candidates)

    return Identification(None, 0.0, note or "unidentified", candidates)
