"""Wire contracts. Money crosses the wire as integer centimes plus a formatted
display string, so no client ever has to do currency arithmetic in a float."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

LanguageCode = Literal["ar", "dz", "kab", "fr", "en"]
NarrativeLevelCode = Literal["child", "standard", "expert"]


# Algerian and French typography groups thousands with a narrow no-break space
# (U+202F) and separates decimals with a comma. Named, because an invisible
# character sitting inside a format string is otherwise impossible to review.
THOUSANDS_SEPARATOR = " "


def format_dzd(centimes: int) -> str:
    """320000 -> '3 200,00 DZD' — Algerian convention."""
    whole, cents = divmod(abs(centimes), 100)
    grouped = f"{whole:,}".replace(",", THOUSANDS_SEPARATOR)
    sign = "-" if centimes < 0 else ""
    return f"{sign}{grouped},{cents:02d} DZD"


class Money(BaseModel):
    centimes: int
    display: str

    @classmethod
    def of(cls, centimes: int) -> Money:
        return cls(centimes=centimes, display=format_dzd(centimes))


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    name: str = Field(min_length=1, max_length=120)
    preferred_language: LanguageCode = "fr"
    user_type: Literal["tourist", "artisan", "guide", "institution"] = "tourist"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshIn(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str
    preferred_language: LanguageCode
    user_type: str
    interests: dict = {}
    home_region: str | None = None


class InterestsIn(BaseModel):
    interests: dict[str, float]

    @field_validator("interests")
    @classmethod
    def clamp(cls, value: dict[str, float]) -> dict[str, float]:
        return {k: max(0.0, min(float(v), 1.0)) for k, v in value.items()}


# --------------------------------------------------------------------------- #
# Sites
# --------------------------------------------------------------------------- #
class SiteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    name: str
    name_ar: str
    region: str
    category: str
    tags: list[str]
    latitude: float
    longitude: float
    summary: str
    summary_ar: str
    unesco: bool
    has_ar: bool
    ar_marker: str | None
    typical_visit_minutes: int
    best_hours: str
    accessibility: str
    entry_fee: Money

    @classmethod
    def of(cls, site) -> SiteOut:
        return cls(
            **{
                field: getattr(site, field)
                for field in (
                    "id", "slug", "name", "name_ar", "region", "category", "tags",
                    "latitude", "longitude", "summary", "summary_ar", "unesco",
                    "has_ar", "ar_marker", "typical_visit_minutes", "best_hours",
                    "accessibility",
                )
            },
            entry_fee=Money.of(site.entry_fee_centimes),
        )


class RecommendationOut(BaseModel):
    site: SiteOut
    score: float
    reason: str


# --------------------------------------------------------------------------- #
# Guide
# --------------------------------------------------------------------------- #
class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    language: LanguageCode = "fr"
    level: NarrativeLevelCode = "standard"
    conversation_id: str | None = None


class SourceOut(BaseModel):
    ref: int
    id: str
    title: str
    source: str
    site_slug: str | None = None
    score: float


class AnswerOut(BaseModel):
    answer: str
    sources: list[SourceOut]
    conversation_id: str | None
    provider: str
    grounded: bool
    refused: bool
    cached: bool = False
    rtl: bool = False


class VisionOut(BaseModel):
    site: SiteOut | None
    confidence: float
    method: str
    narrative: str
    sources: list[SourceOut] = []
    nearby: list[SiteOut] = []


# --------------------------------------------------------------------------- #
# Itineraries
# --------------------------------------------------------------------------- #
class ItineraryRequestIn(BaseModel):
    query: str = Field(min_length=3, max_length=600)
    language: LanguageCode = "fr"
    start_date: date | None = None
    save: bool = True


class StopOut(BaseModel):
    site_id: str | None
    label: str
    arrive_at: str
    dwell_minutes: int
    tip: str
    site: SiteOut | None = None


class DayOut(BaseModel):
    index: int
    travel_km: float
    stops: list[StopOut]


class ItineraryOut(BaseModel):
    id: str | None
    title: str
    days: int
    party_size: int
    budget_band: str
    mobility: str
    interests: list[str]
    language: str
    start_date: date | None
    plan: list[DayOut]


# --------------------------------------------------------------------------- #
# Bookings
# --------------------------------------------------------------------------- #
class ServiceOut(BaseModel):
    id: str
    title: str
    description: str
    price: Money
    duration_minutes: int
    max_party: int
    provider_name: str
    provider_type: str
    region: str
    languages: list[str]
    certified: bool
    rating: float


class BookingIn(BaseModel):
    service_id: str
    scheduled_for: date
    party_size: int = Field(default=1, ge=1, le=20)


class BookingOut(BaseModel):
    id: str
    service_id: str
    service_title: str
    status: str
    scheduled_for: date
    party_size: int
    amount: Money
    created_at: datetime


class BookingStatusIn(BaseModel):
    status: Literal["confirmed", "cancelled", "completed"]


# --------------------------------------------------------------------------- #
# Marketplace
# --------------------------------------------------------------------------- #
class ProductOut(BaseModel):
    id: str
    name: str
    name_ar: str
    category: str
    price: Money
    stock: int
    technique: str
    origin: str
    story: str
    story_is_ai_drafted: bool
    artisan_name: str
    artisan_region: str
    artisan_workshop: str


class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    name_ar: str = ""
    category: str
    price_centimes: int = Field(ge=0)
    stock: int = Field(default=1, ge=0)
    technique: str = ""
    origin: str = ""
    notes: str = Field(default="", max_length=1200)
    language: LanguageCode = "fr"


class OrderIn(BaseModel):
    product_id: str
    quantity: int = Field(default=1, ge=1, le=20)


class OrderOut(BaseModel):
    id: str
    product_id: str
    product_name: str
    quantity: int
    unit_price: Money
    total: Money
    status: str
    created_at: datetime


class ReviewIn(BaseModel):
    site_id: str | None = None
    product_id: str | None = None
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=1000)


# --------------------------------------------------------------------------- #
# Practical services and dashboard
# --------------------------------------------------------------------------- #
class PracticalOut(BaseModel):
    region: str
    emergency: dict[str, str]
    transport: list[dict]
    pharmacies_on_duty: list[dict]
    etiquette: list[str]
    weekend: str
    currency: str


class DashboardOut(BaseModel):
    generated_at: datetime
    cohort_floor: int
    active_visitors: int | None
    average_stay_days: float | None
    by_region: list[dict]
    trends: list[dict]
    suppressed: list[str]
    note: str
