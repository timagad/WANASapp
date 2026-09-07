"""Idempotent seeding: heritage corpus, marketplace, providers, demo accounts.

Run `python -m app.seed` to bring an empty database up. Run it again and nothing
duplicates. Run `python -m app.seed --reindex` after swapping the embedder to
recompute every vector without touching anything else.

The synthetic interaction history at the end exists for one reason: the
collaborative half of the recommender and the k-anonymity floor on the
institutional dashboard are both invisible on an empty database, and a feature
you cannot see is a feature nobody reviews.
"""
from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings import get_embedder, normalize
from app.ai.rag import chunk_document
from app.config import settings
from app.db import SessionLocal, init_db
from app.models import (
    Artisan,
    CraftProduct,
    HeritageChunk,
    InteractionEvent,
    Language,
    Provider,
    ProviderType,
    Service,
    TouristSite,
    User,
    UserType,
)
from app.security import hash_password

SEED_DIR = Path(__file__).parent / "seed_data"
DEMO_PASSWORD = "wanas-demo-2026"


def _load(name: str):
    return json.loads((SEED_DIR / name).read_text(encoding="utf-8"))


def seed_sites(db: Session) -> dict[str, TouristSite]:
    existing = {s.slug: s for s in db.execute(select(TouristSite)).scalars()}
    for record in _load("sites.json"):
        site = existing.get(record["slug"])
        if site is None:
            site = TouristSite(**record)
            db.add(site)
            existing[record["slug"]] = site
        else:
            # Re-running seed should pick up corrected content, not skip it.
            for field, value in record.items():
                setattr(site, field, value)
    db.commit()
    return existing


def seed_corpus(db: Session, sites: dict[str, TouristSite], *, reindex: bool = False) -> int:
    embedder = get_embedder()
    if reindex:
        db.query(HeritageChunk).delete()
        db.commit()

    known_sources = {
        (c.source, c.content[:120]) for c in db.execute(select(HeritageChunk)).scalars()
    }
    written = 0

    for document in _load("corpus.json"):
        site = sites.get(document["site"]) if document["site"] else None
        for index, piece in enumerate(chunk_document(document["content"])):
            fingerprint = (document["source"], piece[:120])
            if fingerprint in known_sources:
                continue
            title = document["title"] if index == 0 else f"{document['title']} ({index + 1})"
            db.add(
                HeritageChunk(
                    site_id=site.id if site else None,
                    title=title,
                    content=piece,
                    search_text=normalize(f"{document['title']} {piece}"),
                    language=document["language"],
                    source=document["source"],
                    # Seed content is editorially reviewed before it ships, which
                    # is what `validated` asserts. Ingestion pipelines added later
                    # must set it deliberately, never by default.
                    validated=True,
                    embedding=embedder.embed(f"{document['title']}\n{piece}"),
                )
            )
            known_sources.add(fingerprint)
            written += 1

    db.commit()
    return written


def seed_market(db: Session) -> None:
    data = _load("market.json")

    artisans: dict[str, Artisan] = {}
    for record in data["artisans"]:
        key = record.pop("key")
        artisan = db.execute(
            select(Artisan).where(Artisan.name == record["name"])
        ).scalar_one_or_none()
        if artisan is None:
            artisan = Artisan(**record)
            db.add(artisan)
            db.flush()
        artisans[key] = artisan

    for record in data["products"]:
        artisan = artisans[record.pop("artisan")]
        exists = db.execute(
            select(CraftProduct).where(
                CraftProduct.name == record["name"], CraftProduct.artisan_id == artisan.id
            )
        ).scalar_one_or_none()
        if exists is None:
            db.add(CraftProduct(artisan_id=artisan.id, story_is_ai_drafted=False, **record))

    sites = {s.slug: s for s in db.execute(select(TouristSite)).scalars()}
    for record in data["providers"]:
        record.pop("key")
        services = record.pop("services")
        provider = db.execute(
            select(Provider).where(Provider.name == record["name"])
        ).scalar_one_or_none()
        if provider is None:
            provider = Provider(
                **{**record, "provider_type": ProviderType(record["provider_type"])}
            )
            db.add(provider)
            db.flush()
        for service in services:
            slug = service.pop("site", None)
            exists = db.execute(
                select(Service).where(
                    Service.title == service["title"], Service.provider_id == provider.id
                )
            ).scalar_one_or_none()
            if exists is None:
                site = sites.get(slug) if slug else None
                db.add(
                    Service(
                        provider_id=provider.id, site_id=site.id if site else None, **service
                    )
                )

    db.commit()


def seed_users(db: Session) -> None:
    demo = [
        ("visiteur@wanas.dz", "Sofiane", Language.fr, UserType.tourist,
         {"history": 0.9, "culture": 0.7, "relaxation": 0.5}),
        ("artisan@wanas.dz", "Amirouche", Language.dz, UserType.artisan, {"crafts": 1.0}),
        ("office@wanas.dz", "Office du tourisme", Language.fr, UserType.institution, {}),
    ]
    for email, name, language, user_type, interests in demo:
        if db.execute(select(User).where(User.email == email)).scalar_one_or_none():
            continue
        db.add(
            User(
                email=email,
                name=name,
                password_hash=hash_password(DEMO_PASSWORD),
                preferred_language=language,
                user_type=user_type,
                interests=interests,
                home_region="Alger" if user_type is UserType.tourist else None,
            )
        )
    db.commit()


def seed_signals(db: Session) -> None:
    """Synthetic visit history, so the recommender and dashboard have something real.

    Cohort sizes are deliberately set above and below `min_cohort` in different
    regions: the dashboard should be seen suppressing a cell, not just filling one.
    """
    if db.execute(select(InteractionEvent).limit(1)).scalar_one_or_none():
        return

    sites = db.execute(select(TouristSite)).scalars().all()
    if not sites:
        return
    by_region: dict[str, list[TouristSite]] = {}
    for site in sites:
        by_region.setdefault(site.region, []).append(site)

    # Above the k-anonymity floor: reported. Below it: withheld.
    cohorts = {"Alger": 68, "Tipaza": 41, "Ghardaïa": 29, "Constantine": 26, "Illizi": 9}
    rng = random.Random(2026)
    now = datetime.now(timezone.utc)

    synthetic: list[User] = []
    for index in range(sum(cohorts.values())):
        user = User(
            email=f"panel{index:03d}@panel.wanas.dz",
            name=f"Panel {index:03d}",
            password_hash=hash_password(DEMO_PASSWORD),
            preferred_language=rng.choice(list(Language)),
            user_type=UserType.tourist,
            interests={},
        )
        db.add(user)
        synthetic.append(user)
    db.flush()

    cursor = 0
    for region, size in cohorts.items():
        regional = by_region.get(region) or sites
        for user in synthetic[cursor : cursor + size]:
            # Two windows, so week-over-week trends are computable.
            for window_start, window_end in ((14, 8), (6, 0)):
                for site in rng.sample(regional, min(len(regional), rng.randint(1, 3))):
                    db.add(
                        InteractionEvent(
                            user_id=user.id,
                            site_id=site.id,
                            kind=rng.choices(
                                ["view", "save", "ar_open", "book"], weights=[6, 3, 2, 1]
                            )[0],
                            region=region,
                            occurred_at=now
                            - timedelta(
                                days=rng.randint(window_end, window_start),
                                hours=rng.randint(0, 23),
                            ),
                        )
                    )
        cursor += size

    db.commit()


def main() -> None:
    reindex = "--reindex" in sys.argv
    init_db()
    with SessionLocal() as db:
        sites = seed_sites(db)
        chunks = seed_corpus(db, sites, reindex=reindex)
        seed_market(db)
        seed_users(db)
        seed_signals(db)

        total_chunks = len(db.execute(select(HeritageChunk)).scalars().all())
        print(
            f"WANAS seed complete — {len(sites)} sites, {total_chunks} heritage chunks "
            f"({chunks} new), LLM: {'claude' if settings.llm_enabled else 'offline-grounded'}"
        )
        print("Demo accounts: visiteur@wanas.dz / artisan@wanas.dz / office@wanas.dz")
        print(f"Demo password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    main()
