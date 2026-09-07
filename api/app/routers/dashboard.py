"""Institutional dashboard — aggregated, anonymised (dossier section 5.6).

The whole value of this endpoint to a tourism office is that it is trustworthy,
and the whole risk of it is re-identification. So suppression is not a filter
applied at the end: any cell backed by fewer than `MIN_COHORT` distinct visitors
is never computed into the response at all, and the response names what it
withheld (AC-7.1).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.config import settings
from app.models import InteractionEvent, Itinerary, UserType
from app.schemas import DashboardOut
from app.security import CurrentUser, DbSession

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def suppress(value: int | float | None, cohort: int) -> int | float | None:
    """Return the value only if its cohort is large enough to hide an individual."""
    return value if cohort >= settings.min_cohort else None


@router.get("", response_model=DashboardOut)
def institutional(
    user: CurrentUser,
    db: DbSession,
    window_days: int = Query(default=7, ge=1, le=90),
) -> DashboardOut:
    if user.user_type != UserType.institution:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Institutional access only")

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=window_days)
    previous_since = since - timedelta(days=window_days)
    suppressed: list[str] = []

    def distinct_visitors(start: datetime, end: datetime, region: str | None = None) -> int:
        stmt = select(func.count(func.distinct(InteractionEvent.user_id))).where(
            InteractionEvent.occurred_at >= start,
            InteractionEvent.occurred_at < end,
            InteractionEvent.user_id.is_not(None),
        )
        if region:
            stmt = stmt.where(InteractionEvent.region == region)
        return int(db.execute(stmt).scalar() or 0)

    total_cohort = distinct_visitors(since, now)
    active = suppress(total_cohort, total_cohort)
    if active is None:
        suppressed.append("active_visitors")

    # Average stay, from planned itinerary length rather than from tracking anyone.
    stay_rows = db.execute(
        select(func.avg(Itinerary.days), func.count(func.distinct(Itinerary.user_id))).where(
            Itinerary.created_at >= since
        )
    ).one()
    stay_cohort = int(stay_rows[1] or 0)
    average_stay = suppress(round(float(stay_rows[0]), 1) if stay_rows[0] else None, stay_cohort)
    if average_stay is None:
        suppressed.append("average_stay_days")

    region_rows = db.execute(
        select(
            InteractionEvent.region,
            func.count(func.distinct(InteractionEvent.user_id)).label("visitors"),
        )
        .where(
            InteractionEvent.occurred_at >= since,
            InteractionEvent.region.is_not(None),
            InteractionEvent.user_id.is_not(None),
        )
        .group_by(InteractionEvent.region)
        .order_by(func.count(func.distinct(InteractionEvent.user_id)).desc())
    ).all()

    by_region: list[dict] = []
    peak = max((int(r.visitors) for r in region_rows), default=0)
    for row in region_rows:
        visitors = int(row.visitors)
        if visitors < settings.min_cohort:
            suppressed.append(f"region:{row.region}")
            continue
        by_region.append(
            {
                "region": row.region,
                "visitors": visitors,
                "share_of_peak": round(visitors / peak, 3) if peak else 0.0,
            }
        )

    trends: list[dict] = []
    for row in region_rows:
        current = int(row.visitors)
        if current < settings.min_cohort:
            continue
        prior = distinct_visitors(previous_since, since, row.region)
        if prior < settings.min_cohort:
            # A change computed against a tiny prior window leaks that window.
            suppressed.append(f"trend:{row.region}")
            continue
        trends.append(
            {
                "region": row.region,
                "change_pct": round((current - prior) / prior * 100, 1),
                "direction": "up" if current >= prior else "down",
            }
        )

    return DashboardOut(
        generated_at=now,
        cohort_floor=settings.min_cohort,
        active_visitors=active,
        average_stay_days=average_stay,
        by_region=by_region,
        trends=trends,
        suppressed=suppressed,
        note=(
            f"Every figure covers at least {settings.min_cohort} distinct visitors. "
            "Cells below that threshold are withheld, not rounded. No individual "
            "identifier is exposed by this endpoint."
        ),
    )
