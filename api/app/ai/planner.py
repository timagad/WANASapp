"""Itinerary planner.

A visitor types one sentence — "je veux passer 3 jours à Alger avec mes parents,
entre histoire et détente" — and gets a day-by-day plan. Two stages:

1. `parse_trip_request` turns the sentence into constraints. Deterministic and
   multilingual, because this must work with no API key (NFR-6) and because a
   parser you can unit-test beats a parser you can only eyeball.
2. `build_plan` lays the selected sites across days under a travel budget, so no
   day sends a family 300 km between two stops (AC-2.3).

The language model is not in this path. It writes the prose tips afterwards;
the structure is the planner's, and stays correct without it.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from app.ai.embeddings import normalize

# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
INTEREST_KEYWORDS: dict[str, list[str]] = {
    "history": ["histoire", "historique", "romain", "antique", "ruines", "patrimoine",
                "history", "historic", "roman", "ancient", "ruins", "heritage",
                "تاريخ", "تاريخي", "روماني", "اثار", "آثار", "قديم", "امزruy"],
    "nature": ["nature", "randonnee", "randonnée", "montagne", "mer", "plage", "desert",
               "désert", "hiking", "mountain", "sea", "beach", "طبيعه", "طبيعة",
               "بحر", "جبل", "صحرا", "صحراء", "شاطئ"],
    "spirituality": ["spiritualite", "spiritualité", "mosquee", "mosquée", "religieux",
                     "zaouia", "spiritual", "mosque", "religious",
                     "روحاني", "مسجد", "جامع", "زاويه", "زاوية", "ديني"],
    "gastronomy": ["cuisine", "gastronomie", "manger", "restaurant", "food", "eat",
                   "ماكله", "ماكلة", "اكل", "طعام", "مطعم"],
    "crafts": ["artisanat", "artisan", "poterie", "tapis", "bijoux", "crafts", "pottery",
               "rug", "jewellery", "jewelry", "صناعه", "صناعة", "حرفه", "حرفة",
               "فخار", "زربيه", "زربية", "حلي"],
    "relaxation": ["detente", "détente", "repos", "calme", "tranquille", "relax", "rest",
                   "quiet", "راحه", "راحة", "هدوء", "تريح"],
    "culture": ["culture", "musee", "musée", "art", "museum", "ثقافه", "ثقافة", "متحف", "فن"],
    "family": ["famille", "enfants", "parents", "family", "children", "kids",
               "عائله", "عائلة", "دراري", "ولاد", "والدين"],
}

MOBILITY_LIMITED = [
    "parents", "grands-parents", "personnes agees", "âgées", "fauteuil", "poussette",
    "elderly", "wheelchair", "stroller", "limited mobility",
    "كبار السن", "الوالدين", "كرسي", "معاق",
]

BUDGET_KEYWORDS = {
    "low": ["pas cher", "petit budget", "economique", "économique", "cheap", "budget",
            "رخيص", "بلا فلوس", "ميزانيه صغيره"],
    "high": ["luxe", "premium", "confort", "luxury", "فخم", "راقي"],
}

REGION_ALIASES = {
    "alger": "Alger", "algiers": "Alger", "الجزائر العاصمه": "Alger", "العاصمه": "Alger",
    "دزاير": "Alger", "الجزائر": "Alger",
    "tipaza": "Tipaza", "tipasa": "Tipaza", "تيبازه": "Tipaza", "تيبازة": "Tipaza",
    "ghardaia": "Ghardaïa", "ghardaïa": "Ghardaïa", "mzab": "Ghardaïa",
    "غردايه": "Ghardaïa", "غرداية": "Ghardaïa", "ميزاب": "Ghardaïa",
    "constantine": "Constantine", "قسنطينه": "Constantine", "قسنطينة": "Constantine",
    "oran": "Oran", "وهران": "Oran",
    "tlemcen": "Tlemcen", "تلمسان": "Tlemcen",
    "batna": "Batna", "timgad": "Batna", "تيمقاد": "Batna", "باتنه": "Batna",
    "setif": "Sétif", "sétif": "Sétif", "djemila": "Sétif", "djémila": "Sétif",
    "سطيف": "Sétif", "جميله": "Sétif", "جميلة": "Sétif",
    "tamanrasset": "Tamanrasset", "hoggar": "Tamanrasset", "ahaggar": "Tamanrasset",
    "تمنراست": "Tamanrasset", "الهقار": "Tamanrasset",
    "djanet": "Illizi", "tassili": "Illizi", "جانت": "Illizi",
    "tizi ouzou": "Tizi Ouzou", "kabylie": "Tizi Ouzou", "تيزي وزو": "Tizi Ouzou",
    "msila": "M'Sila", "m'sila": "M'Sila", "beni hammad": "M'Sila", "المسيله": "M'Sila",
}

NUMBER_WORDS = {
    "un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six ": 6, "seven": 7,
    "يوم": 1, "يومين": 2, "ثلاثه": 3, "ثلاثة": 3, "اربعه": 4, "أربعة": 4, "خمسه": 5,
    "خمسة": 5, "سته": 6, "ستة": 6, "سبعه": 7, "سبعة": 7,
}

_DAY_WORD = r"(?:jours?|days?|ايام|يوم)"


def _folded(*words: str) -> tuple[str, ...]:
    """Fold keywords through the same normaliser the query goes through.

    Every comparison in this module is normalised-against-normalised. Mixing raw
    and folded forms is exactly how "العائلة" silently stopped matching "عائلة".
    """
    return tuple(normalize(w) for w in words)


_PARTY_FAMILY = _folded("famille", "family", "parents", "عائلة", "والدين", "دراري")
_PARTY_COUPLE = _folded("couple", "زوجين", "زوجي")
_WEEKEND = _folded("عطلة نهاية الاسبوع", "ويكاند")
_TWO_DAYS = normalize("يومين")


@dataclass
class TripRequest:
    days: int = 2
    party_size: int = 1
    interests: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    budget_band: str = "mid"
    mobility: str = "easy"
    language: str = "fr"
    raw: str = ""


def _detect_days(folded: str) -> int:
    match = re.search(rf"(\d+)\s*{_DAY_WORD}", folded)
    if match:
        return max(1, min(int(match.group(1)), 14))
    if re.search(r"\bweek[- ]?end\b", folded) or any(w in folded for w in _WEEKEND):
        return 2
    if _TWO_DAYS in folded:
        return 2
    for word, value in NUMBER_WORDS.items():
        if re.search(rf"{re.escape(normalize(word))}\s*{_DAY_WORD}", folded):
            return value
    return 2


def _detect_party(folded: str) -> int:
    match = re.search(r"(\d+)\s*(?:personnes?|people|persons|اشخاص)", folded)
    if match:
        return max(1, min(int(match.group(1)), 20))
    if any(k in folded for k in _PARTY_FAMILY):
        return 4
    if any(k in folded for k in _PARTY_COUPLE):
        return 2
    return 1


def parse_trip_request(query: str, *, language: str = "fr") -> TripRequest:
    """Extract trip constraints from a free-text request in any supported language."""
    folded = normalize(query)

    interests: list[str] = []
    for interest, keywords in INTEREST_KEYWORDS.items():
        if any(normalize(k) in folded for k in keywords):
            interests.append(interest)

    regions: list[str] = []
    for alias, region in REGION_ALIASES.items():
        if normalize(alias) in folded and region not in regions:
            regions.append(region)

    budget = "mid"
    for band, keywords in BUDGET_KEYWORDS.items():
        if any(normalize(k) in folded for k in keywords):
            budget = band
            break

    mobility = "limited" if any(normalize(k) in folded for k in MOBILITY_LIMITED) else "easy"

    return TripRequest(
        days=_detect_days(folded),
        party_size=_detect_party(folded),
        interests=interests or ["history", "culture"],
        regions=regions,
        budget_band=budget,
        mobility=mobility,
        language=language,
        raw=query.strip(),
    )


def interest_weights(interests: list[str]) -> dict[str, float]:
    """Turn a list of stated interests into the weight vector the recommender wants."""
    if not interests:
        return {}
    # First-mentioned interests weigh slightly more; the visitor led with them.
    step = 0.15 / max(len(interests), 1)
    return {name: round(1.0 - i * step, 3) for i, name in enumerate(interests)}


# --------------------------------------------------------------------------- #
# Layout
# --------------------------------------------------------------------------- #
DAY_START_MINUTES = 9 * 60
DAY_END_MINUTES = 18 * 60
LUNCH_MINUTES = 13 * 60
AVERAGE_SPEED_KMH = 45.0
# One day of a holiday should not be spent in a car.
MAX_TRAVEL_KM_PER_DAY = 220.0


@dataclass
class PlannedStop:
    site_id: str | None
    label: str
    arrive_at: str
    dwell_minutes: int
    tip: str = ""


@dataclass
class PlannedDay:
    index: int
    stops: list[PlannedStop] = field(default_factory=list)
    travel_km: float = 0.0


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(h))


def _clock(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def build_plan(sites: list[dict], request: TripRequest, *, lunch_label: str = "Lunch") -> list[PlannedDay]:
    """Lay ranked sites across days, nearest-neighbour within each day.

    `sites` are dicts with id, name, latitude, longitude, typical_visit_minutes,
    accessibility and an optional tip — already ordered best-first by the
    recommender. The planner only decides *when* and *with what* each is paired.
    """
    pool = list(sites)
    if request.mobility == "limited":
        pool = [s for s in pool if s.get("accessibility") != "hard"] or pool

    days: list[PlannedDay] = []
    remaining = pool[:]

    for day_index in range(1, request.days + 1):
        if not remaining:
            break
        day = PlannedDay(index=day_index)
        # Anchor on the best remaining site, then walk to whatever is nearest.
        current = remaining.pop(0)
        clock = DAY_START_MINUTES
        lunch_inserted = False
        previous_point: tuple[float, float] | None = None

        while True:
            if previous_point is not None:
                leg = haversine_km(previous_point, (current["latitude"], current["longitude"]))
                if day.travel_km + leg > MAX_TRAVEL_KM_PER_DAY:
                    remaining.insert(0, current)
                    break
                day.travel_km += leg
                clock += int(leg / AVERAGE_SPEED_KMH * 60)

            dwell = int(current.get("typical_visit_minutes") or 90)
            if clock + dwell > DAY_END_MINUTES:
                remaining.insert(0, current)
                break

            if not lunch_inserted and clock >= LUNCH_MINUTES:
                day.stops.append(
                    PlannedStop(
                        site_id=None,
                        label=lunch_label,
                        arrive_at=_clock(clock),
                        dwell_minutes=60,
                        tip=current.get("lunch_tip", ""),
                    )
                )
                clock += 60
                lunch_inserted = True

            day.stops.append(
                PlannedStop(
                    site_id=current["id"],
                    label=current["name"],
                    arrive_at=_clock(clock),
                    dwell_minutes=dwell,
                    tip=current.get("tip", ""),
                )
            )
            clock += dwell
            previous_point = (current["latitude"], current["longitude"])

            if not remaining:
                break
            remaining.sort(key=lambda s: haversine_km(previous_point, (s["latitude"], s["longitude"])))
            current = remaining.pop(0)

        if not lunch_inserted and day.stops:
            day.stops.append(
                PlannedStop(
                    site_id=None,
                    label=lunch_label,
                    arrive_at=_clock(min(clock, DAY_END_MINUTES)),
                    dwell_minutes=60,
                )
            )
        if day.stops:
            days.append(day)

    return days
