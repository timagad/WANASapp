"""Unit tests for the AI layer's decision rules.

These run with no database, no Redis and no API key — the same conditions the
platform has to survive in a demo room.
"""
from __future__ import annotations

import asyncio

import pytest

from app.ai.embeddings import HashingEmbedder, cosine, normalize, script_of, tokenize
from app.ai.planner import (
    MAX_TRAVEL_KM_PER_DAY,
    TripRequest,
    build_plan,
    haversine_km,
    interest_weights,
    parse_trip_request,
)
from app.ai.provider import OfflineProvider, Passage
from app.ai.rag import chunk_document, fuse
from app.ai.recommender import (
    blend_weight,
    build_cooccurrence,
    collaborative_score,
    content_score,
    rank,
)
from app.ai.vision import GEO_CONFIDENT_KM, geographic_candidates
from app.config import settings


# --------------------------------------------------------------------------- #
# Embeddings
# --------------------------------------------------------------------------- #
def test_normalize_folds_arabic_orthography():
    # Diacritics, alef variants, ya and ta marbuta all collapse, so an unvowelled
    # Darija query still matches vowelled MSA corpus text.
    assert normalize("الجَزَائِر") == normalize("الجزاير")
    assert normalize("إسلام") == normalize("اسلام")
    assert normalize("قلعة") == normalize("قلعه")


def test_tokenize_drops_stopwords_in_every_language():
    assert "de" not in tokenize("le site de Tipaza")
    assert "tipaza" in tokenize("le site de Tipaza")
    assert "في" not in tokenize("تيبازة في الجزائر")


def test_tokenize_strips_darija_function_words_down_to_the_topic():
    # "Where is Tipaza and what is in it" carries exactly one content word.
    assert tokenize("وين تيبازة وواش كاين فيها") == [normalize("تيبازة")]


def test_a_fused_arabic_conjunction_is_still_a_stopword():
    # "وواش" is "و" + "واش"; without prefix handling it survives as a token
    # and dilutes the one word that matters.
    assert tokenize("وواش") == []


def test_script_detection():
    assert script_of("tipaza") == "la"
    assert script_of("تيبازه") == "ar"
    assert script_of("ⵜⵉⴱⴰⵣⴰ") == "tfng"


def test_arabic_and_latin_text_do_not_match_through_hash_collisions():
    # Features are namespaced by script. Before that, an Arabic question could
    # out-score the right passage against an unrelated French one.
    embedder = HashingEmbedder()
    arabic = embedder.embed("الآثار الرومانية في تيبازة على ساحل البحر المتوسط")
    latin = embedder.embed("Kabyle pottery from Maatkas, shaped without a wheel")
    assert abs(cosine(arabic, latin)) < 0.1


def test_embedding_ranks_related_text_above_unrelated():
    embedder = HashingEmbedder()
    query = embedder.embed("ruines romaines de Tipaza au bord de la mer")
    related = embedder.embed("Tipasa, colonie romaine sur la côte méditerranéenne")
    unrelated = embedder.embed("bijouterie touarègue en argent et ébène à Djanet")
    assert cosine(query, related) > cosine(query, unrelated)


def test_embedding_is_deterministic_and_normalised():
    embedder = HashingEmbedder()
    first = embedder.embed("Timgad")
    assert first == embedder.embed("Timgad")
    assert cosine(first, first) == pytest.approx(1.0, abs=1e-9)


def test_embedding_of_empty_text_is_safe():
    embedder = HashingEmbedder()
    assert cosine(embedder.embed(""), embedder.embed("Timgad")) == 0.0


# --------------------------------------------------------------------------- #
# Retrieval
# --------------------------------------------------------------------------- #
def test_chunk_document_keeps_paragraphs_whole_when_they_fit():
    text = "Premier paragraphe court.\n\nSecond paragraphe court."
    assert chunk_document(text, target_chars=700) == [text]


def test_chunk_document_splits_long_paragraphs_on_sentences():
    sentence = "Tipasa fut un comptoir punique puis une colonie romaine. "
    chunks = chunk_document(sentence * 40, target_chars=300)
    assert len(chunks) > 1
    assert all(len(c) <= 500 for c in chunks)


def test_fuse_prefers_dense_but_lexical_can_rescue():
    # A chunk the dense pass missed but that names the site exactly still ranks.
    weak_dense_strong_lexical = fuse(0.05, 0.09)
    assert weak_dense_strong_lexical > settings.relevance_floor


def test_fuse_keeps_irrelevant_chunks_under_the_refusal_floor():
    assert fuse(0.02, 0.0) < settings.relevance_floor


def test_same_language_chunk_outranks_a_tie():
    assert fuse(0.3, 0.05, same_language=True) > fuse(0.3, 0.05, same_language=False)


# --------------------------------------------------------------------------- #
# Provider — grounding contract
# --------------------------------------------------------------------------- #
def _passage(**kwargs) -> Passage:
    base = dict(
        id="c1",
        title="Tipasa",
        content="Tipasa fut un comptoir punique. Elle devint une colonie romaine au Ier siècle.",
        source="UNESCO",
        language="fr",
        score=0.4,
        site_slug="tipasa",
    )
    return Passage(**{**base, **kwargs})


def test_offline_provider_refuses_when_nothing_was_retrieved():
    answer = asyncio.run(
        OfflineProvider().answer_guide(question="Qui a bâti X ?", passages=[], language="fr")
    )
    assert answer.refused is True
    assert answer.sources == []


def test_offline_provider_cites_every_passage_it_uses():
    answer = asyncio.run(
        OfflineProvider().answer_guide(
            question="Parle-moi de Tipasa", passages=[_passage()], language="fr"
        )
    )
    assert answer.refused is False
    assert "[1]" in answer.text
    assert answer.sources[0]["site_slug"] == "tipasa"


def test_offline_provider_answers_darija_in_darija():
    answer = asyncio.run(
        OfflineProvider().answer_guide(
            question="واش كاين في تيبازة؟", passages=[_passage()], language="dz"
        )
    )
    # The Darija lead-in, not the French one.
    assert "قاعدة التراث" in answer.text


# --------------------------------------------------------------------------- #
# Trip parsing
# --------------------------------------------------------------------------- #
def test_parse_french_request():
    request = parse_trip_request(
        "Je veux passer 3 jours à Alger avec mes parents, entre histoire et détente"
    )
    assert request.days == 3
    assert request.regions == ["Alger"]
    assert "history" in request.interests
    assert "relaxation" in request.interests
    assert request.mobility == "limited"  # "mes parents"
    assert request.party_size == 4


def test_parse_darija_request():
    request = parse_trip_request("نحب نروح يومين لتيبازة مع العائلة", language="dz")
    assert request.days == 2
    assert request.regions == ["Tipaza"]
    assert request.party_size == 4


def test_parse_english_request_with_budget():
    request = parse_trip_request("5 days in Ghardaia on a small budget, crafts and nature")
    assert request.days == 5
    assert request.regions == ["Ghardaïa"]
    assert request.budget_band == "low"
    assert {"crafts", "nature"} <= set(request.interests)


def test_parse_falls_back_to_sane_defaults():
    request = parse_trip_request("bonjour")
    assert request.days == 2
    assert request.interests  # never empty, or the recommender has nothing to score


def test_interest_weights_lead_with_the_first_interest():
    weights = interest_weights(["history", "nature", "crafts"])
    assert weights["history"] > weights["crafts"]
    assert max(weights.values()) <= 1.0


# --------------------------------------------------------------------------- #
# Itinerary layout
# --------------------------------------------------------------------------- #
def _site(id_: str, lat: float, lon: float, minutes: int = 90, access: str = "moderate") -> dict:
    return {
        "id": id_,
        "name": id_,
        "latitude": lat,
        "longitude": lon,
        "typical_visit_minutes": minutes,
        "accessibility": access,
        "tip": "",
    }


def test_haversine_matches_known_distance():
    # Algiers to Tipasa is roughly 60 km as the crow flies.
    distance = haversine_km((36.7538, 3.0588), (36.5936, 2.4489))
    assert 50 < distance < 70


def test_plan_never_exceeds_the_daily_travel_budget():
    far_apart = [
        _site("alger", 36.75, 3.06),
        _site("oran", 35.70, -0.66),
        _site("tamanrasset", 22.78, 5.52),
        _site("annaba", 36.90, 7.76),
    ]
    days = build_plan(far_apart, TripRequest(days=3))
    assert days
    assert all(day.travel_km <= MAX_TRAVEL_KM_PER_DAY for day in days)


def test_plan_includes_a_lunch_stop_each_day():
    sites = [_site(f"s{i}", 36.75 + i * 0.01, 3.06) for i in range(4)]
    days = build_plan(sites, TripRequest(days=1), lunch_label="Déjeuner")
    assert any(stop.label == "Déjeuner" for stop in days[0].stops)


def test_plan_drops_hard_sites_for_limited_mobility():
    sites = [_site("easy", 36.75, 3.06), _site("steep", 36.76, 3.07, access="hard")]
    days = build_plan(sites, TripRequest(days=1, mobility="limited"))
    labels = {stop.label for day in days for stop in day.stops}
    assert "steep" not in labels


def test_plan_keeps_hard_sites_when_they_are_the_only_option():
    # Better an honest warning on the stop than an empty itinerary.
    sites = [_site("steep", 36.76, 3.07, access="hard")]
    days = build_plan(sites, TripRequest(days=1, mobility="limited"))
    assert any(stop.label == "steep" for day in days for stop in day.stops)


def test_plan_stops_are_chronological():
    sites = [_site(f"s{i}", 36.75 + i * 0.01, 3.06, minutes=60) for i in range(4)]
    days = build_plan(sites, TripRequest(days=1))
    times = [stop.arrive_at for stop in days[0].stops]
    assert times == sorted(times)


# --------------------------------------------------------------------------- #
# Recommender
# --------------------------------------------------------------------------- #
def test_cold_start_uses_content_only():
    assert blend_weight(0.0) == 0.0


def test_collaborative_share_grows_with_evidence_but_stays_capped():
    assert blend_weight(1.0) < blend_weight(5.0) <= 0.6


def test_content_score_rewards_stated_interests_over_fame():
    wanted = content_score({"crafts": 1.0}, ["crafts"], popularity=0.1)
    famous = content_score({"crafts": 1.0}, ["nature"], popularity=1.0)
    assert wanted > famous


def test_content_score_does_not_reward_tag_spam():
    focused = content_score({"history": 1.0}, ["history"])
    spammed = content_score({"history": 1.0}, ["history"] + [f"filler{i}" for i in range(9)])
    assert focused > spammed


def test_cooccurrence_is_symmetric_and_bounded():
    similarity = build_cooccurrence({"u1": {"a": 1.0, "b": 1.0}, "u2": {"a": 1.0, "b": 1.0}})
    assert similarity["a"]["b"] == pytest.approx(similarity["b"]["a"])
    assert similarity["a"]["b"] <= 1.0 + 1e-9


def test_collaborative_score_is_zero_without_a_profile():
    assert collaborative_score("a", {}, {"a": {"b": 1.0}}) == 0.0


def test_rank_excludes_already_seen_and_explicitly_excluded_sites():
    candidates = [
        {"id": "a", "tags": ["history"], "popularity": 0.5, "region": "Alger"},
        {"id": "b", "tags": ["history"], "popularity": 0.5, "region": "Alger"},
        {"id": "c", "tags": ["history"], "popularity": 0.5, "region": "Alger"},
    ]
    ranked = rank(
        candidates,
        interests={"history": 1.0},
        profile={"a": 1.0},
        similarity={},
        exclude={"b"},
    )
    assert [r.site_id for r in ranked] == ["c"]


def test_cold_start_ranking_does_not_crash_without_any_history():
    ranked = rank(
        [{"id": "a", "tags": ["nature"], "popularity": 0.9, "region": "Alger"}],
        interests={},
        profile={},
        similarity={},
    )
    assert len(ranked) == 1
    assert ranked[0].reason == "your-interests"


# --------------------------------------------------------------------------- #
# Vision
# --------------------------------------------------------------------------- #
def test_geographic_confidence_is_high_at_the_site_and_zero_far_away():
    sites = [
        {"slug": "tipasa", "latitude": 36.5936, "longitude": 2.4489},
        {"slug": "timgad", "latitude": 35.4842, "longitude": 6.4686},
    ]
    at_tipasa = geographic_candidates(sites, (36.5936, 2.4489))
    assert at_tipasa[0]["slug"] == "tipasa"
    assert at_tipasa[0]["distance_km"] <= GEO_CONFIDENT_KM
    assert at_tipasa[0]["confidence"] > 0.9
    assert at_tipasa[1]["confidence"] == 0.0


def test_identification_without_a_fix_or_a_vision_model_reports_unidentified():
    from app.ai.vision import identify

    result = asyncio.run(
        identify(
            image_bytes=b"not-a-real-photo",
            media_type="image/jpeg",
            sites=[{"slug": "tipasa", "latitude": 36.59, "longitude": 2.45}],
            provider=OfflineProvider(),
        )
    )
    assert result.site_slug is None
    assert result.confidence == 0.0
