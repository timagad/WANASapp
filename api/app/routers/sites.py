from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.ai.planner import haversine_km
from app.ai.recommender import Recommender
from app.models import InteractionEvent, Itinerary, ItineraryStop, Review, TouristSite
from app.schemas import RecommendationOut, ReviewIn, SiteOut
from app.security import CurrentUser, DbSession, MaybeUser

router = APIRouter(prefix="/sites", tags=["sites"])


@router.get("", response_model=list[SiteOut])
def list_sites(
    db: DbSession,
    region: str | None = None,
    category: str | None = None,
    unesco: bool | None = None,
    has_ar: bool | None = None,
    near_lat: float | None = None,
    near_lon: float | None = None,
    radius_km: float = Query(default=50.0, gt=0, le=2000),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[SiteOut]:
    stmt = select(TouristSite)
    if region:
        stmt = stmt.where(TouristSite.region == region)
    if category:
        stmt = stmt.where(TouristSite.category == category)
    if unesco is not None:
        stmt = stmt.where(TouristSite.unesco.is_(unesco))
    if has_ar is not None:
        stmt = stmt.where(TouristSite.has_ar.is_(has_ar))

    sites = db.execute(stmt).scalars().all()

    if near_lat is not None and near_lon is not None:
        point = (near_lat, near_lon)
        with_distance = [
            (s, haversine_km(point, (s.latitude, s.longitude))) for s in sites
        ]
        sites = [s for s, d in sorted(with_distance, key=lambda x: x[1]) if d <= radius_km]

    return [SiteOut.of(s) for s in sites[:limit]]


@router.get("/regions", response_model=list[dict])
def list_regions(db: DbSession) -> list[dict]:
    rows = db.execute(select(TouristSite.region, TouristSite.id)).all()
    counts: dict[str, int] = {}
    for region, _ in rows:
        counts[region] = counts.get(region, 0) + 1
    return [{"region": r, "sites": c} for r, c in sorted(counts.items())]


@router.get("/recommended", response_model=list[RecommendationOut])
def recommended(
    db: DbSession,
    user: MaybeUser,
    limit: int = Query(default=8, ge=1, le=40),
) -> list[RecommendationOut]:
    """Hybrid recommendations. Works signed out — cold start is the normal case."""
    interests = dict(user.interests or {}) if user else {}
    exclude: set[str] = set()
    if user:
        # Never recommend what is already on their plan (AC-3.2).
        planned = db.execute(
            select(ItineraryStop.site_id)
            .join(Itinerary, Itinerary.id == ItineraryStop.itinerary_id)
            .where(Itinerary.user_id == user.id, ItineraryStop.site_id.is_not(None))
        ).scalars().all()
        exclude = {sid for sid in planned if sid}

    results = Recommender(db).for_user(
        user_id=user.id if user else None,
        interests=interests,
        home_region=user.home_region if user else None,
        exclude=exclude,
        limit=limit,
    )
    return [
        RecommendationOut(site=SiteOut.of(site), score=round(scored.score, 4), reason=scored.reason)
        for site, scored in results
    ]


@router.get("/{slug}", response_model=SiteOut)
def get_site(slug: str, db: DbSession, user: MaybeUser) -> SiteOut:
    site = db.execute(select(TouristSite).where(TouristSite.slug == slug)).scalar_one_or_none()
    if site is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Site not found")
    db.add(
        InteractionEvent(
            user_id=user.id if user else None, site_id=site.id, kind="view", region=site.region
        )
    )
    db.commit()
    return SiteOut.of(site)


@router.post("/{slug}/events", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def record_event(slug: str, kind: str, db: DbSession, user: MaybeUser) -> None:
    """Record a save / ar_open / book signal. Feeds the recommender and dashboard."""
    if kind not in {"view", "save", "book", "ar_open"}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown event kind")
    site = db.execute(select(TouristSite).where(TouristSite.slug == slug)).scalar_one_or_none()
    if site is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Site not found")
    db.add(
        InteractionEvent(
            user_id=user.id if user else None, site_id=site.id, kind=kind, region=site.region
        )
    )
    db.commit()


@router.post("/reviews", status_code=status.HTTP_201_CREATED)
def add_review(payload: ReviewIn, user: CurrentUser, db: DbSession) -> dict:
    if not payload.site_id and not payload.product_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Review needs a target")

    existing = None
    if payload.site_id:
        existing = db.execute(
            select(Review).where(Review.user_id == user.id, Review.site_id == payload.site_id)
        ).scalar_one_or_none()

    if existing:
        existing.rating = payload.rating
        existing.comment = payload.comment
        db.add(existing)
        db.commit()
        return {"id": existing.id, "updated": True}

    review = Review(
        user_id=user.id,
        site_id=payload.site_id,
        product_id=payload.product_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(review)
    db.commit()
    return {"id": review.id, "updated": False}
