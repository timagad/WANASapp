"""Domain model — section 4 of the technical architecture, plus the tables the
RAG engine, the recommender and the institutional dashboard need.

Money is stored as integer centimes DZD everywhere. No floats in money paths.
"""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config import settings


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Language(str, enum.Enum):
    """Darija is a first-class locale, not a fallback for Arabic."""

    ar = "ar"      # Modern Standard Arabic
    dz = "dz"      # Algerian Darija
    kab = "kab"    # Tamazight
    fr = "fr"
    en = "en"


class UserType(str, enum.Enum):
    tourist = "tourist"
    artisan = "artisan"
    guide = "guide"
    institution = "institution"


class BookingStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"


class ProviderType(str, enum.Enum):
    guide = "guide"
    host = "host"
    activity = "activity"
    transport = "transport"


class NarrativeLevel(str, enum.Enum):
    child = "child"
    standard = "standard"
    expert = "expert"


# --------------------------------------------------------------------------- #
# People
# --------------------------------------------------------------------------- #
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(120))
    preferred_language: Mapped[Language] = mapped_column(
        Enum(Language, name="language"), default=Language.fr
    )
    user_type: Mapped[UserType] = mapped_column(
        Enum(UserType, name="user_type"), default=UserType.tourist
    )
    # Free-form interest weights, e.g. {"history": 0.9, "nature": 0.4}
    interests: Mapped[dict] = mapped_column(JSONB, default=dict)
    home_region: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    itineraries: Mapped[list[Itinerary]] = relationship(back_populates="user")
    bookings: Mapped[list[Booking]] = relationship(back_populates="user")
    reviews: Mapped[list[Review]] = relationship(back_populates="user")


class Provider(Base):
    """Certified guide, host, activity operator or transporter."""

    __tablename__ = "providers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(160))
    provider_type: Mapped[ProviderType] = mapped_column(Enum(ProviderType, name="provider_type"))
    region: Mapped[str] = mapped_column(String(80), index=True)
    languages: Mapped[list[str]] = mapped_column(ARRAY(String(8)), default=list)
    bio: Mapped[str] = mapped_column(Text, default="")
    certified: Mapped[bool] = mapped_column(Boolean, default=False)
    rating: Mapped[float] = mapped_column(Float, default=0.0)

    services: Mapped[list[Service]] = relationship(back_populates="provider")


class Service(Base):
    """A bookable unit sold by a provider. Price in centimes DZD."""

    __tablename__ = "services"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    provider_id: Mapped[str] = mapped_column(ForeignKey("providers.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    price_centimes: Mapped[int] = mapped_column(Integer)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=120)
    max_party: Mapped[int] = mapped_column(Integer, default=8)
    site_id: Mapped[str | None] = mapped_column(ForeignKey("tourist_sites.id"), nullable=True)

    provider: Mapped[Provider] = relationship(back_populates="services")


class Artisan(Base):
    __tablename__ = "artisans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(160))
    workshop: Mapped[str] = mapped_column(String(160), default="")
    region: Mapped[str] = mapped_column(String(80), index=True)
    craft: Mapped[str] = mapped_column(String(80), default="")
    story: Mapped[str] = mapped_column(Text, default="")
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    products: Mapped[list[CraftProduct]] = relationship(back_populates="artisan")


# --------------------------------------------------------------------------- #
# Places
# --------------------------------------------------------------------------- #
class TouristSite(Base):
    __tablename__ = "tourist_sites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    name_ar: Mapped[str] = mapped_column(String(160), default="")
    region: Mapped[str] = mapped_column(String(80), index=True)
    category: Mapped[str] = mapped_column(String(60), index=True)
    # Interest tags the content-based recommender scores against.
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(40)), default=list)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    summary: Mapped[str] = mapped_column(Text, default="")
    summary_ar: Mapped[str] = mapped_column(Text, default="")
    unesco: Mapped[bool] = mapped_column(Boolean, default=False)
    has_ar: Mapped[bool] = mapped_column(Boolean, default=False)
    ar_marker: Mapped[str | None] = mapped_column(String(60), nullable=True)
    typical_visit_minutes: Mapped[int] = mapped_column(Integer, default=90)
    best_hours: Mapped[str] = mapped_column(String(60), default="09:00-17:00")
    entry_fee_centimes: Mapped[int] = mapped_column(Integer, default=0)
    accessibility: Mapped[str] = mapped_column(String(40), default="moderate")
    popularity: Mapped[float] = mapped_column(Float, default=0.5)

    reviews: Mapped[list[Review]] = relationship(back_populates="site")


class HeritageChunk(Base):
    """One editorially-validated passage of the heritage corpus, embedded for RAG."""

    __tablename__ = "heritage_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    site_id: Mapped[str | None] = mapped_column(
        ForeignKey("tourist_sites.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    # Diacritic-folded copy of `content`; the lexical half of the hybrid
    # retriever indexes this so an unvowelled Darija query still matches.
    search_text: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(8), default="fr", index=True)
    source: Mapped[str] = mapped_column(String(300))
    # Nothing is indexed until an editor has validated it (architecture section 10).
    validated: Mapped[bool] = mapped_column(Boolean, default=False)
    embedding = mapped_column(Vector(settings.embedding_dim))

    __table_args__ = (Index("heritage_chunk_site_lang_idx", "site_id", "language"),)


# --------------------------------------------------------------------------- #
# Trips
# --------------------------------------------------------------------------- #
class Itinerary(Base):
    __tablename__ = "itineraries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    days: Mapped[int] = mapped_column(Integer, default=1)
    party_size: Mapped[int] = mapped_column(Integer, default=1)
    budget_band: Mapped[str] = mapped_column(String(20), default="mid")
    mobility: Mapped[str] = mapped_column(String(20), default="easy")
    interests: Mapped[list[str]] = mapped_column(ARRAY(String(40)), default=list)
    language: Mapped[str] = mapped_column(String(8), default="fr")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped[User] = relationship(back_populates="itineraries")
    stops: Mapped[list[ItineraryStop]] = relationship(
        back_populates="itinerary",
        cascade="all, delete-orphan",
        order_by="ItineraryStop.day_index, ItineraryStop.position",
    )


class ItineraryStop(Base):
    __tablename__ = "itinerary_stops"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    itinerary_id: Mapped[str] = mapped_column(
        ForeignKey("itineraries.id", ondelete="CASCADE"), index=True
    )
    site_id: Mapped[str | None] = mapped_column(ForeignKey("tourist_sites.id"), nullable=True)
    day_index: Mapped[int] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String(160))
    arrive_at: Mapped[str] = mapped_column(String(5), default="09:00")
    dwell_minutes: Mapped[int] = mapped_column(Integer, default=90)
    tip: Mapped[str] = mapped_column(Text, default="")

    itinerary: Mapped[Itinerary] = relationship(back_populates="stops")


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    service_id: Mapped[str] = mapped_column(ForeignKey("services.id"), index=True)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, name="booking_status"), default=BookingStatus.pending
    )
    scheduled_for: Mapped[date] = mapped_column(Date)
    party_size: Mapped[int] = mapped_column(Integer, default=1)
    amount_centimes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped[User] = relationship(back_populates="bookings")


# --------------------------------------------------------------------------- #
# Marketplace
# --------------------------------------------------------------------------- #
class CraftProduct(Base):
    __tablename__ = "craft_products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    artisan_id: Mapped[str] = mapped_column(ForeignKey("artisans.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    name_ar: Mapped[str] = mapped_column(String(160), default="")
    category: Mapped[str] = mapped_column(String(60), index=True)
    price_centimes: Mapped[int] = mapped_column(Integer)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    technique: Mapped[str] = mapped_column(String(160), default="")
    origin: Mapped[str] = mapped_column(String(120), default="")
    story: Mapped[str] = mapped_column(Text, default="")
    story_is_ai_drafted: Mapped[bool] = mapped_column(Boolean, default=False)

    artisan: Mapped[Artisan] = relationship(back_populates="products")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("craft_products.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price_centimes: Mapped[int] = mapped_column(Integer)
    total_centimes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="placed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    site_id: Mapped[str | None] = mapped_column(ForeignKey("tourist_sites.id"), nullable=True)
    product_id: Mapped[str | None] = mapped_column(ForeignKey("craft_products.id"), nullable=True)
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped[User] = relationship(back_populates="reviews")
    site: Mapped[TouristSite] = relationship(back_populates="reviews")

    __table_args__ = (UniqueConstraint("user_id", "site_id", name="uq_review_user_site"),)


# --------------------------------------------------------------------------- #
# Signals — feed the recommender and the anonymised dashboard
# --------------------------------------------------------------------------- #
class InteractionEvent(Base):
    __tablename__ = "interaction_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    site_id: Mapped[str | None] = mapped_column(ForeignKey("tourist_sites.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(30), index=True)  # view | save | book | ar_open
    region: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, index=True
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    language: Mapped[str] = mapped_column(String(8), default="fr")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(12))  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    sources: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
