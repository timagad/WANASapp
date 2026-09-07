"""End-to-end tests against a real PostgreSQL + pgvector database.

The unit suite deliberately needs nothing running. This suite is the other half:
it exercises the paths that only exist once there is a database — vector
retrieval, the grounding contract on real corpus content, transactional stock,
and the dashboard's k-anonymity floor over real rows.

    docker compose up -d db cache
    cd api && .venv/Scripts/python -m pytest tests/test_integration.py

The whole module skips, loudly but without failing, when no database answers, so
`pytest` stays green on a laptop with nothing running.

WARNING: this seeds and writes to the database named in DATABASE_URL. Point it
at a scratch database, not one whose data you care about.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import settings


def _database_available() -> bool:
    try:
        from app.db import engine

        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _database_available(),
    reason=f"no database at {settings.database_url.rsplit('@', 1)[-1]} — run `docker compose up -d db`",
)


@pytest.fixture(scope="module")
def client():
    from app.main import app
    from app.seed import main as seed

    seed()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def visitor(client: TestClient) -> dict:
    """A fresh account per run, so reruns never collide on the unique email."""
    email = f"test-{uuid.uuid4().hex[:10]}@wanas.test"
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "wanas-demo-2026",
            "name": "Test Visitor",
            "preferred_language": "fr",
        },
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    return {"email": email, "headers": {"Authorization": f"Bearer {token}"}}


# --------------------------------------------------------------------------- #
# Corpus and retrieval
# --------------------------------------------------------------------------- #
def test_seed_indexed_the_corpus(client: TestClient):
    from app.db import SessionLocal
    from app.models import HeritageChunk

    with SessionLocal() as db:
        chunks = db.query(HeritageChunk).all()
    assert len(chunks) > 20
    assert all(c.validated for c in chunks), "unvalidated content must never be indexed"
    assert all(c.embedding is not None for c in chunks)
    assert all(c.search_text for c in chunks)


def test_guide_answers_a_french_question_with_citations(client: TestClient):
    response = client.post(
        "/guide/ask",
        json={"question": "Parle-moi du site romain de Tipasa", "language": "fr"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["refused"] is False
    assert body["sources"], "a grounded answer must cite something"
    assert any("Tipasa" in s["title"] or "Tipaza" in s["title"] for s in body["sources"])


def test_guide_answers_a_darija_question_from_the_arabic_corpus(client: TestClient):
    response = client.post(
        "/guide/ask", json={"question": "واش كاين في تيبازة؟", "language": "dz"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["rtl"] is True
    assert body["refused"] is False
    assert body["sources"]


def test_a_darija_question_is_answered_from_arabic_script_sources(client: TestClient):
    """The asymmetry this corpus round closed.

    Constantine used to be documented in French only, so a Darija speaker got a
    French passage while a French speaker got a native one. Every site now
    carries Arabic, and the same-language boost should surface it.
    """
    from app.db import SessionLocal
    from app.models import HeritageChunk

    response = client.post(
        "/guide/ask",
        json={"question": "شحال طول جسر سيدي مسيد في قسنطينة", "language": "dz"},
    )
    body = response.json()
    assert body["refused"] is False
    assert body["sources"]

    with SessionLocal() as db:
        languages = {
            db.get(HeritageChunk, source["id"]).language for source in body["sources"]
        }
    assert languages & {"ar", "dz"}, f"Darija question answered only from {languages}"


def test_guide_refuses_rather_than_inventing(client: TestClient):
    # Nothing in the Algerian heritage corpus can answer this.
    response = client.post(
        "/guide/ask",
        json={"question": "Quel est le cours de clôture du Nasdaq hier ?", "language": "fr"},
    )
    body = response.json()
    assert body["refused"] is True
    assert body["sources"] == []


def test_hybrid_retrieval_finds_a_proper_noun_the_dense_pass_would_dilute(client: TestClient):
    response = client.post(
        "/guide/ask", json={"question": "Qal'a des Beni Hammad", "language": "fr"}
    )
    body = response.json()
    assert body["refused"] is False
    assert any("Hammad" in s["title"] for s in body["sources"])


# --------------------------------------------------------------------------- #
# Catalogue and recommendations
# --------------------------------------------------------------------------- #
def test_catalogue_and_unesco_filter(client: TestClient):
    everything = client.get("/sites").json()
    assert len(everything) >= 14
    unesco = client.get("/sites?unesco=true").json()
    assert len(unesco) == 7, "Algeria has seven UNESCO World Heritage sites"


def test_recommendations_work_signed_out(client: TestClient):
    # Cold start is the normal case, not an edge case.
    response = client.get("/sites/recommended?limit=5")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 5
    assert all(r["reason"] == "your-interests" for r in body)


def test_recommendations_respect_stated_interests(client: TestClient, visitor: dict):
    client.put(
        "/auth/me/interests", json={"interests": {"crafts": 1.0}}, headers=visitor["headers"]
    )
    body = client.get("/sites/recommended?limit=5", headers=visitor["headers"]).json()
    assert any("crafts" in r["site"]["tags"] for r in body)


# --------------------------------------------------------------------------- #
# Itineraries
# --------------------------------------------------------------------------- #
def test_itinerary_is_generated_saved_and_reloadable(client: TestClient, visitor: dict):
    response = client.post(
        "/itineraries/generate",
        json={
            "query": "3 jours à Alger avec mes parents, entre histoire et détente",
            "language": "fr",
            "save": True,
        },
        headers=visitor["headers"],
    )
    assert response.status_code == 200, response.text
    plan = response.json()

    assert plan["days"] == 3
    assert plan["mobility"] == "limited"
    assert plan["party_size"] == 4
    assert plan["plan"], "an itinerary with no days is not an itinerary"
    assert all(day["travel_km"] <= 220 for day in plan["plan"])
    assert all(stop["arrive_at"] for day in plan["plan"] for stop in day["stops"])
    assert plan["id"]

    reloaded = client.get(f"/itineraries/{plan['id']}", headers=visitor["headers"]).json()
    assert reloaded["title"] == plan["title"]
    assert len(reloaded["plan"]) == len(plan["plan"])


def test_itinerary_of_another_user_is_not_readable(client: TestClient, visitor: dict):
    mine = client.post(
        "/itineraries/generate",
        json={"query": "2 jours à Tipaza", "language": "fr", "save": True},
        headers=visitor["headers"],
    ).json()

    other = client.post(
        "/auth/register",
        json={
            "email": f"other-{uuid.uuid4().hex[:8]}@wanas.test",
            "password": "wanas-demo-2026",
            "name": "Other",
            "preferred_language": "en",
        },
    ).json()
    headers = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.get(f"/itineraries/{mine['id']}", headers=headers).status_code == 404


# --------------------------------------------------------------------------- #
# Bookings and marketplace
# --------------------------------------------------------------------------- #
def test_booking_lifecycle_and_illegal_transition(client: TestClient, visitor: dict):
    service = client.get("/services").json()[0]
    created = client.post(
        "/bookings",
        json={
            "service_id": service["id"],
            "scheduled_for": (date.today() + timedelta(days=14)).isoformat(),
            "party_size": 2,
        },
        headers=visitor["headers"],
    )
    assert created.status_code == 201, created.text
    booking = created.json()
    assert booking["status"] == "pending"
    # Integer arithmetic, not float multiplication.
    assert booking["amount"]["centimes"] == service["price"]["centimes"] * 2

    confirmed = client.patch(
        f"/bookings/{booking['id']}", json={"status": "confirmed"}, headers=visitor["headers"]
    )
    assert confirmed.status_code == 200

    cancelled = client.patch(
        f"/bookings/{booking['id']}", json={"status": "cancelled"}, headers=visitor["headers"]
    )
    assert cancelled.status_code == 200

    revived = client.patch(
        f"/bookings/{booking['id']}", json={"status": "confirmed"}, headers=visitor["headers"]
    )
    assert revived.status_code == 409, "a cancelled booking must not come back to life"


def test_booking_a_past_date_is_refused(client: TestClient, visitor: dict):
    service = client.get("/services").json()[0]
    response = client.post(
        "/bookings",
        json={
            "service_id": service["id"],
            "scheduled_for": (date.today() - timedelta(days=1)).isoformat(),
            "party_size": 1,
        },
        headers=visitor["headers"],
    )
    assert response.status_code == 422


def test_order_decrements_stock_and_cannot_oversell(client: TestClient, visitor: dict):
    product = client.get("/marketplace/products").json()[0]
    before = product["stock"]

    order = client.post(
        "/marketplace/orders",
        json={"product_id": product["id"], "quantity": 1},
        headers=visitor["headers"],
    )
    assert order.status_code == 201, order.text
    assert order.json()["total"]["centimes"] == product["price"]["centimes"]

    after = client.get(f"/marketplace/products/{product['id']}").json()
    assert after["stock"] == before - 1

    oversell = client.post(
        "/marketplace/orders",
        json={"product_id": product["id"], "quantity": after["stock"] + 5},
        headers=visitor["headers"],
    )
    assert oversell.status_code == 409


def test_product_stories_name_their_technique_and_origin(client: TestClient):
    for product in client.get("/marketplace/products").json():
        assert product["story"], "a craft listing without its story is just an object"
        assert product["technique"]
        assert product["origin"]


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
def test_dashboard_is_closed_to_ordinary_visitors(client: TestClient, visitor: dict):
    assert client.get("/dashboard", headers=visitor["headers"]).status_code == 403


def test_dashboard_reports_large_cohorts_and_withholds_small_ones(client: TestClient):
    login = client.post(
        "/auth/login", json={"email": "office@wanas.dz", "password": "wanas-demo-2026"}
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    body = client.get("/dashboard?window_days=7", headers=headers).json()

    assert body["cohort_floor"] == settings.min_cohort
    assert all(row["visitors"] >= settings.min_cohort for row in body["by_region"])
    # The seed puts Illizi below the floor on purpose, so suppression is visible.
    assert any(cell.startswith("region:") for cell in body["suppressed"])
    assert "Illizi" not in [row["region"] for row in body["by_region"]]


def test_health_reports_the_active_provider(client: TestClient):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["llm"] in {"claude", "offline-grounded"}
    assert set(body["languages"]) == {"ar", "dz", "kab", "fr", "en"}
