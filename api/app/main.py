"""WANAS API entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.cache import get_client
from app.config import settings
from app.db import init_db
from app.routers import auth, bookings, dashboard, guide, itineraries, marketplace, practical, sites


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "WANAS — your smart travel companion in Algeria. Conversational heritage "
        "guide grounded in a validated corpus (RAG), hybrid itinerary planner, "
        "bookings, crafts marketplace and an anonymised institutional dashboard."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    auth.router,
    sites.router,
    guide.router,
    itineraries.router,
    bookings.router,
    marketplace.router,
    practical.router,
    dashboard.router,
):
    app.include_router(router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    """What is actually wired up right now — used by the web app's status strip."""
    return {
        "status": "ok",
        "llm": "claude" if settings.llm_enabled else "offline-grounded",
        "cache": "redis" if get_client() is not None else "disabled",
        "languages": ["ar", "dz", "kab", "fr", "en"],
    }
