from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.models import Booking, BookingStatus, InteractionEvent, Provider, Service
from app.schemas import BookingIn, BookingOut, BookingStatusIn, Money, ServiceOut
from app.security import CurrentUser, DbSession

router = APIRouter(tags=["bookings"])

# The only transitions a booking may make. Anything else is a client bug and is
# rejected rather than silently applied (AC-4.1).
ALLOWED_TRANSITIONS: dict[BookingStatus, set[BookingStatus]] = {
    BookingStatus.pending: {BookingStatus.confirmed, BookingStatus.cancelled},
    BookingStatus.confirmed: {BookingStatus.completed, BookingStatus.cancelled},
    BookingStatus.cancelled: set(),
    BookingStatus.completed: set(),
}


def _service_out(service: Service, provider: Provider) -> ServiceOut:
    return ServiceOut(
        id=service.id,
        title=service.title,
        description=service.description,
        price=Money.of(service.price_centimes),
        duration_minutes=service.duration_minutes,
        max_party=service.max_party,
        provider_name=provider.name,
        provider_type=provider.provider_type.value,
        region=provider.region,
        languages=list(provider.languages or []),
        certified=provider.certified,
        rating=provider.rating,
    )


@router.get("/services", response_model=list[ServiceOut])
def list_services(
    db: DbSession,
    region: str | None = None,
    provider_type: str | None = None,
    language: str | None = None,
    certified_only: bool = False,
    limit: int = Query(default=40, ge=1, le=100),
) -> list[ServiceOut]:
    stmt = select(Service, Provider).join(Provider, Provider.id == Service.provider_id)
    if region:
        stmt = stmt.where(Provider.region == region)
    if provider_type:
        stmt = stmt.where(Provider.provider_type == provider_type)
    if certified_only:
        stmt = stmt.where(Provider.certified.is_(True))

    rows = db.execute(stmt.limit(limit)).all()
    results = [
        _service_out(service, provider)
        for service, provider in rows
        if not language or language in (provider.languages or [])
    ]
    return results


@router.post("/bookings", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking(payload: BookingIn, user: CurrentUser, db: DbSession) -> BookingOut:
    service = db.get(Service, payload.service_id)
    if service is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service not found")
    if payload.scheduled_for < date.today():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Cannot book a past date")
    if payload.party_size > service.max_party:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"This service takes at most {service.max_party} people",
        )

    booking = Booking(
        user_id=user.id,
        service_id=service.id,
        scheduled_for=payload.scheduled_for,
        party_size=payload.party_size,
        # Integer arithmetic end to end — never a float multiplication on money.
        amount_centimes=service.price_centimes * payload.party_size,
    )
    db.add(booking)
    if service.site_id:
        db.add(InteractionEvent(user_id=user.id, site_id=service.site_id, kind="book"))
    db.commit()

    return BookingOut(
        id=booking.id,
        service_id=service.id,
        service_title=service.title,
        status=booking.status.value,
        scheduled_for=booking.scheduled_for,
        party_size=booking.party_size,
        amount=Money.of(booking.amount_centimes),
        created_at=booking.created_at,
    )


@router.get("/bookings", response_model=list[BookingOut])
def my_bookings(user: CurrentUser, db: DbSession) -> list[BookingOut]:
    rows = db.execute(
        select(Booking, Service)
        .join(Service, Service.id == Booking.service_id)
        .where(Booking.user_id == user.id)
        .order_by(Booking.created_at.desc())
    ).all()
    return [
        BookingOut(
            id=b.id,
            service_id=b.service_id,
            service_title=s.title,
            status=b.status.value,
            scheduled_for=b.scheduled_for,
            party_size=b.party_size,
            amount=Money.of(b.amount_centimes),
            created_at=b.created_at,
        )
        for b, s in rows
    ]


@router.patch("/bookings/{booking_id}", response_model=BookingOut)
def update_booking(
    booking_id: str, payload: BookingStatusIn, user: CurrentUser, db: DbSession
) -> BookingOut:
    booking = db.get(Booking, booking_id)
    if booking is None or booking.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")

    target = BookingStatus(payload.status)
    if target not in ALLOWED_TRANSITIONS[booking.status]:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot move a booking from {booking.status.value} to {target.value}",
        )

    booking.status = target
    db.add(booking)
    db.commit()

    service = db.get(Service, booking.service_id)
    return BookingOut(
        id=booking.id,
        service_id=booking.service_id,
        service_title=service.title if service else "",
        status=booking.status.value,
        scheduled_for=booking.scheduled_for,
        party_size=booking.party_size,
        amount=Money.of(booking.amount_centimes),
        created_at=booking.created_at,
    )
