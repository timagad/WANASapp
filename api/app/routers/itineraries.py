from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.ai.planner import build_plan, interest_weights, parse_trip_request
from app.ai.recommender import Recommender
from app.models import Itinerary, ItineraryStop, TouristSite
from app.schemas import DayOut, ItineraryOut, ItineraryRequestIn, SiteOut, StopOut
from app.security import CurrentUser, DbSession, MaybeUser

router = APIRouter(prefix="/itineraries", tags=["itineraries"])

LUNCH_LABEL = {
    "fr": "Déjeuner",
    "en": "Lunch",
    "ar": "الغداء",
    "dz": "الغدا",
    "kab": "Imekli",
}

TITLE_TEMPLATE = {
    "fr": "{regions} en {days} jour(s)",
    "en": "{regions} in {days} day(s)",
    "ar": "{regions} في {days} يوم",
    "dz": "{regions} في {days} يام",
    "kab": "{regions} deg {days} n wussan",
}

TIPS = {
    "early": {
        "fr": "Arrivez tôt : moins de monde et moins de chaleur.",
        "en": "Arrive early — fewer crowds, cooler air.",
        "ar": "احضر مبكرًا: ازدحام أقل وحرارة أخف.",
        "dz": "أجي بكري: ما كاينش الزحمه والحرارة أقل.",
        "kab": "As-d zik: drus n medden, drus n tafuktt.",
    },
    "ar": {
        "fr": "Site compatible réalité augmentée : pointez la caméra pour voir la reconstruction.",
        "en": "Augmented reality available here — point your camera to see the reconstruction.",
        "ar": "الواقع المعزّز متاح هنا: وجّه الكاميرا لرؤية إعادة البناء.",
        "dz": "الواقع المعزّز خدّام هنا: وجّه الكاميرا وشوف كيفاش كان.",
        "kab": "Tilawt tessemɣeṛ tella dagi: sekcem takamiṛat.",
    },
    "hard": {
        "fr": "Terrain irrégulier : prévoyez de bonnes chaussures.",
        "en": "Uneven ground — wear proper shoes.",
        "ar": "الأرض غير مستوية: البس حذاءً مناسبًا.",
        "dz": "الأرض ماشي مستويه: لبس صباط مليح.",
        "kab": "Akal ur d-yeṣfi ara: elses irkasen igerrzen.",
    },
    "unesco": {
        "fr": "Classé au patrimoine mondial de l'UNESCO.",
        "en": "Inscribed on the UNESCO World Heritage List.",
        "ar": "مُدرج في قائمة التراث العالمي لليونسكو.",
        "dz": "مسجّل في التراث العالمي تاع اليونسكو.",
        "kab": "Yura deg umuɣ n uzref n umaḍal UNESCO.",
    },
}


def _tip(site: TouristSite, language: str) -> str:
    """Compose the practical line under a stop, in the visitor's language."""
    lines: list[str] = []
    if site.unesco:
        lines.append(TIPS["unesco"].get(language, TIPS["unesco"]["fr"]))
    if site.has_ar:
        lines.append(TIPS["ar"].get(language, TIPS["ar"]["fr"]))
    if site.accessibility == "hard":
        lines.append(TIPS["hard"].get(language, TIPS["hard"]["fr"]))
    if not lines:
        lines.append(TIPS["early"].get(language, TIPS["early"]["fr"]))
    return " ".join(lines)


@router.post("/generate", response_model=ItineraryOut)
def generate(payload: ItineraryRequestIn, db: DbSession, user: MaybeUser) -> ItineraryOut:
    request = parse_trip_request(payload.query, language=payload.language)
    interests = interest_weights(request.interests)

    ranked = Recommender(db).for_user(
        user_id=user.id if user else None,
        interests=interests,
        home_region=user.home_region if user else None,
        limit=60,
    )
    sites = [site for site, _ in ranked]

    # A named region is a hard constraint, not a preference: someone asking for
    # Algiers does not want Tamanrasset in the list, however well it scores.
    if request.regions:
        in_region = [s for s in sites if s.region in request.regions]
        if in_region:
            sites = in_region

    if not sites:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No sites available to plan with")

    by_id = {s.id: s for s in sites}
    plan = build_plan(
        [
            {
                "id": s.id,
                "name": s.name if payload.language not in {"ar", "dz"} or not s.name_ar else s.name_ar,
                "latitude": s.latitude,
                "longitude": s.longitude,
                "typical_visit_minutes": s.typical_visit_minutes,
                "accessibility": s.accessibility,
                "tip": _tip(s, payload.language),
            }
            for s in sites
        ],
        request,
        lunch_label=LUNCH_LABEL.get(payload.language, LUNCH_LABEL["fr"]),
    )

    regions = request.regions or sorted({s.region for s in sites[:4]})
    title = TITLE_TEMPLATE.get(payload.language, TITLE_TEMPLATE["fr"]).format(
        regions=" · ".join(regions[:3]), days=request.days
    )

    days_out = [
        DayOut(
            index=day.index,
            travel_km=round(day.travel_km, 1),
            stops=[
                StopOut(
                    site_id=stop.site_id,
                    label=stop.label,
                    arrive_at=stop.arrive_at,
                    dwell_minutes=stop.dwell_minutes,
                    tip=stop.tip,
                    site=SiteOut.of(by_id[stop.site_id]) if stop.site_id in by_id else None,
                )
                for stop in day.stops
            ],
        )
        for day in plan
    ]

    itinerary_id: str | None = None
    if payload.save and user is not None:
        itinerary = Itinerary(
            user_id=user.id,
            title=title,
            start_date=payload.start_date,
            days=request.days,
            party_size=request.party_size,
            budget_band=request.budget_band,
            mobility=request.mobility,
            interests=request.interests,
            language=payload.language,
        )
        db.add(itinerary)
        db.flush()
        for day in plan:
            for position, stop in enumerate(day.stops):
                db.add(
                    ItineraryStop(
                        itinerary_id=itinerary.id,
                        site_id=stop.site_id,
                        day_index=day.index,
                        position=position,
                        label=stop.label,
                        arrive_at=stop.arrive_at,
                        dwell_minutes=stop.dwell_minutes,
                        tip=stop.tip,
                    )
                )
        db.commit()
        itinerary_id = itinerary.id

    return ItineraryOut(
        id=itinerary_id,
        title=title,
        days=request.days,
        party_size=request.party_size,
        budget_band=request.budget_band,
        mobility=request.mobility,
        interests=request.interests,
        language=payload.language,
        start_date=payload.start_date,
        plan=days_out,
    )


@router.get("", response_model=list[dict])
def my_itineraries(user: CurrentUser, db: DbSession) -> list[dict]:
    rows = db.execute(
        select(Itinerary).where(Itinerary.user_id == user.id).order_by(Itinerary.created_at.desc())
    ).scalars().all()
    return [
        {
            "id": i.id,
            "title": i.title,
            "days": i.days,
            "start_date": i.start_date.isoformat() if i.start_date else None,
            "stops": len(i.stops),
            "language": i.language,
        }
        for i in rows
    ]


@router.get("/{itinerary_id}", response_model=ItineraryOut)
def get_itinerary(itinerary_id: str, user: CurrentUser, db: DbSession) -> ItineraryOut:
    itinerary = db.get(Itinerary, itinerary_id)
    if itinerary is None or itinerary.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Itinerary not found")

    site_ids = {s.site_id for s in itinerary.stops if s.site_id}
    sites = (
        db.execute(select(TouristSite).where(TouristSite.id.in_(site_ids))).scalars().all()
        if site_ids
        else []
    )
    by_id = {s.id: s for s in sites}

    grouped: dict[int, list[StopOut]] = {}
    for stop in itinerary.stops:
        grouped.setdefault(stop.day_index, []).append(
            StopOut(
                site_id=stop.site_id,
                label=stop.label,
                arrive_at=stop.arrive_at,
                dwell_minutes=stop.dwell_minutes,
                tip=stop.tip,
                site=SiteOut.of(by_id[stop.site_id]) if stop.site_id in by_id else None,
            )
        )

    return ItineraryOut(
        id=itinerary.id,
        title=itinerary.title,
        days=itinerary.days,
        party_size=itinerary.party_size,
        budget_band=itinerary.budget_band,
        mobility=itinerary.mobility,
        interests=list(itinerary.interests or []),
        language=itinerary.language,
        start_date=itinerary.start_date,
        plan=[
            DayOut(index=index, travel_km=0.0, stops=stops)
            for index, stops in sorted(grouped.items())
        ],
    )


@router.delete("/{itinerary_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_itinerary(itinerary_id: str, user: CurrentUser, db: DbSession) -> None:
    itinerary = db.get(Itinerary, itinerary_id)
    if itinerary is None or itinerary.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Itinerary not found")
    db.delete(itinerary)
    db.commit()
