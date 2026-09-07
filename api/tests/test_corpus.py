"""Tests over the shipped heritage corpus itself.

Retrieval quality depends on two things that can each be wrong independently:
the embedder, and the corpus. The unit tests cover the embedder on synthetic
strings; these cover the real content, by running the dense half of the retriever
in memory. No database needed — which means a bad corpus edit fails on a laptop,
not in production.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.ai.embeddings import cosine, get_embedder, normalize
from app.ai.rag import chunk_document

SEED_DIR = Path(__file__).resolve().parent.parent / "app" / "seed_data"

SITES = json.loads((SEED_DIR / "sites.json").read_text(encoding="utf-8"))
CORPUS = json.loads((SEED_DIR / "corpus.json").read_text(encoding="utf-8"))
MARKET = json.loads((SEED_DIR / "market.json").read_text(encoding="utf-8"))

SITE_SLUGS = {site["slug"] for site in SITES}


# --------------------------------------------------------------------------- #
# Integrity
# --------------------------------------------------------------------------- #
def test_every_corpus_document_points_at_a_real_site_or_is_thematic():
    for document in CORPUS:
        assert document["site"] is None or document["site"] in SITE_SLUGS, document["title"]


def test_every_document_carries_a_source():
    # A passage with no source cannot be cited, and an uncitable passage must
    # never reach the guide.
    for document in CORPUS:
        assert document["source"].strip(), document["title"]
        assert len(document["content"]) > 200, document["title"]


def test_every_ar_enabled_site_declares_a_marker():
    for site in SITES:
        if site["has_ar"]:
            assert site["ar_marker"], site["slug"]


def test_unesco_sites_are_the_seven_inscribed_ones():
    inscribed = sorted(site["slug"] for site in SITES if site["unesco"])
    assert inscribed == sorted(
        [
            "casbah-alger",
            "djemila",
            "qalaa-beni-hammad",
            "tassili-najjer",
            "timgad",
            "tipasa",
            "vallee-mzab",
        ]
    )


def test_coordinates_fall_inside_algeria():
    # Roughly: 18-38 N, -9 to 12 E. A transposed lat/lon lands outside this.
    for site in SITES:
        assert 18 <= site["latitude"] <= 38, site["slug"]
        assert -9 <= site["longitude"] <= 12, site["slug"]


def test_every_site_has_arabic_name_and_summary():
    for site in SITES:
        assert site["name_ar"].strip(), site["slug"]
        assert site["summary_ar"].strip(), site["slug"]


def test_every_site_is_documented_in_french_and_arabic():
    """The corpus floor: no site may be reachable in one language only.

    An Arabic or Darija speaker asking about Constantine must not be answered
    out of a French passage while a French speaker gets a native one — that
    asymmetry is exactly what the project exists to remove.
    """
    covered: dict[str, set[str]] = {}
    for document in CORPUS:
        if document["site"]:
            covered.setdefault(document["site"], set()).add(document["language"])

    missing = {
        site["slug"]: sorted({"fr", "ar"} - covered.get(site["slug"], set()))
        for site in SITES
        if not {"fr", "ar"} <= covered.get(site["slug"], set())
    }
    assert not missing, f"sites missing a language: {missing}"


def test_darija_is_represented_beyond_a_token_entry():
    # Darija is the stated differentiator; one practical sheet does not deliver it.
    darija = [d for d in CORPUS if d["language"] == "dz"]
    assert len(darija) >= 8
    assert sum(1 for d in darija if d["site"]) >= 4, "Darija needs heritage content, not only tips"


def test_prices_are_integer_centimes():
    for product in MARKET["products"]:
        assert isinstance(product["price_centimes"], int)
        # A four-figure DZD price expressed in centimes is at least 5 digits;
        # this catches a price accidentally entered in dinars.
        assert product["price_centimes"] >= 10000, product["name"]
    for provider in MARKET["providers"]:
        for service in provider["services"]:
            assert isinstance(service["price_centimes"], int)


def test_marketplace_references_resolve():
    artisan_keys = {a["key"] for a in MARKET["artisans"]}
    for product in MARKET["products"]:
        assert product["artisan"] in artisan_keys, product["name"]
    for provider in MARKET["providers"]:
        for service in provider["services"]:
            assert service["site"] in SITE_SLUGS, service["title"]


# --------------------------------------------------------------------------- #
# Retrieval over the real content
# --------------------------------------------------------------------------- #
def _index() -> list[tuple[str | None, str, list[float]]]:
    """Chunk and embed the whole corpus, exactly as `app.seed` does."""
    embedder = get_embedder()
    entries = []
    for document in CORPUS:
        for piece in chunk_document(document["content"]):
            entries.append(
                (document["site"], document["title"], embedder.embed(f"{document['title']}\n{piece}"))
            )
    return entries


INDEX = _index()


def _best_site(query: str) -> str | None:
    embedder = get_embedder()
    vector = embedder.embed(query)
    site, _, _ = max(INDEX, key=lambda entry: cosine(vector, entry[2]))
    return site


def test_the_corpus_chunks_into_a_usable_index():
    assert len(INDEX) >= len(CORPUS)
    assert all(any(vector) for _, _, vector in INDEX)


@pytest.mark.parametrize(
    "query,expected",
    [
        ("les ruines romaines de Tipasa au bord de la mer", "tipasa"),
        ("l'arc de Trajan et le théâtre de Timgad", "timgad"),
        ("la Casbah d'Alger et ses ruelles en escalier", "casbah-alger"),
        ("les cinq ksour ibadites de la vallée du M'Zab", "vallee-mzab"),
        ("gravures rupestres du Tassili n'Ajjer", "tassili-najjer"),
        ("le minaret hammadide de la Qal'a des Beni Hammad", "qalaa-beni-hammad"),
        ("le jardin botanique du Hamma à Alger", "jardin-essai-hamma"),
    ],
)
def test_french_queries_retrieve_the_right_site(query: str, expected: str):
    assert _best_site(query) == expected


@pytest.mark.parametrize(
    "query,expected",
    [
        ("الآثار الرومانية في تيبازة", "tipasa"),
        ("قوس تراجان في تيمقاد", "timgad"),
        ("مدينة جميلة الرومانية في سطيف", "djemila"),
        ("قصبة الجزائر العثمانية", "casbah-alger"),
        ("قصور وادي ميزاب الإباضية", "vallee-mzab"),
        ("النقوش الصخرية في الطاسيلي ناجر", "tassili-najjer"),
        ("مئذنة قلعة بني حماد", "qalaa-beni-hammad"),
        ("شروق الشمس من أسكرم في الهقار", "assekrem-hoggar"),
        ("حديقة التجارب بالحامة", "jardin-essai-hamma"),
        ("مئذنة جامع الجزائر الأعظم", "djamaa-el-djazair"),
        ("كنيسة السيدة الإفريقية في بولوغين", "notre-dame-afrique"),
        ("جسر سيدي مسيد في قسنطينة", "constantine-ponts"),
        ("مئذنة المنصورة في تلمسان", "tlemcen-mansourah"),
        ("حصن سانتا كروز في وهران", "santa-cruz-oran"),
    ],
)
def test_every_site_is_reachable_by_an_arabic_query(query: str, expected: str):
    """One case per site, so a coverage gap fails here rather than in front of a visitor.

    Scored on the dense channel alone — the hardest case. Production adds
    lexical fusion and a same-language boost on top of this.
    """
    assert _best_site(query) == expected


@pytest.mark.parametrize(
    "query,expected",
    [
        ("كيفاش ندور في القصبة", "casbah-alger"),
        ("وين تيبازة وواش كاين فيها", "tipasa"),
        ("شحال طول جسر سيدي مسيد في قسنطينة", "constantine-ponts"),
        ("كيفاش نطلع لسانتا كروز في وهران", "santa-cruz-oran"),
        ("واش كاين في غرداية وميزاب", "vallee-mzab"),
    ],
)
def test_darija_queries_retrieve_the_right_site(query: str, expected: str):
    assert _best_site(query) == expected


@pytest.mark.parametrize(
    "query",
    [
        "كيفاش نتحرك في دزاير العاصمة",
        "واش ندير في الصحرا والهقار",
        "قداش الارقام تاع الاستعجالات في الجزائر",
    ],
)
def test_darija_practical_questions_reach_the_thematic_sheets(query: str):
    # Thematic documents carry no site, which is how they are recognised.
    assert _best_site(query) is None


def test_english_query_retrieves_the_right_site():
    assert _best_site("Roman colony on the Mediterranean coast at Tipasa") == "tipasa"


def test_a_darija_query_beats_every_wrong_site_by_a_clear_margin():
    """Written the way someone actually types it: no diacritics, loose spelling,
    and four function words around the one that matters.

    The margin is measured against the best passage from a *different* site, not
    against the runner-up overall. Once a site has several documents its own
    second-best crowds the top of the ranking, and comparing against that would
    make this test fail for the good reason that coverage improved.
    """
    embedder = get_embedder()
    vector = embedder.embed("وين تيبازة وواش كاين فيها")

    best = max(INDEX, key=lambda entry: cosine(vector, entry[2]))
    best_wrong = max(
        (entry for entry in INDEX if entry[0] != "tipasa"),
        key=lambda entry: cosine(vector, entry[2]),
    )

    assert best[0] == "tipasa"
    # Win clearly, not by a hair: a narrow argmax here is hash luck, not retrieval.
    assert cosine(vector, best[2]) > 1.8 * cosine(vector, best_wrong[2])


def test_corpus_normalisation_is_stable():
    # The lexical index stores folded text; folding must be idempotent, or a
    # reindex would silently change what matches.
    for document in CORPUS:
        folded = normalize(document["content"])
        assert normalize(folded) == folded, document["title"]
