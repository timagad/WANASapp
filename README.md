# WANAS — ونّاس

**Your smart travel companion in Algeria.** An AI heritage guide that never
invents a fact, a planner that turns one sentence into a real itinerary, a
marketplace that puts an artisan's own story next to their work, and an
augmented-reality layer that stands a ruined monument back up.

Built to the specification in `WANAS_Project_Dossier_EN_2.md` and
`WANAS_Architecture_Technique_EN.md` — IA Tour Algérie 2026, Phase 1 MVP.

---

## Run it

```powershell
.\scripts\demo.ps1        # or ./scripts/demo.sh on macOS/Linux
```

That copies `.env`, brings the stack up, waits until the API genuinely answers,
and prints the URLs and demo accounts. `docker compose up --build` does the same
thing without the hand-holding.

- Web app → <http://localhost:3000> (redirects to your browser's language)
- API docs → <http://localhost:8000/docs>
- Presenting it? **[docs/demo-script.md](docs/demo-script.md)** is a four-minute
  beat-by-beat walkthrough, including what to do when something breaks on stage.

The database is seeded automatically on first boot: 14 sites, 46 validated
heritage documents, five artisans, five providers and a synthetic visitor panel.
Every site is documented in **both French and Arabic**; eight documents are in
Darija and six in English.

**No API key is required.** With `ANTHROPIC_API_KEY` blank, the guide answers
extractively from the retrieved corpus and labels itself offline. Set the key and
the same endpoints call Claude instead. Nothing else in the codebase changes —
see [Provider independence](#provider-independence).

Demo accounts (password `wanas-demo-2026`):

| Account | Role | What it unlocks |
|---|---|---|
| `visiteur@wanas.dz` | tourist | Saved itineraries, bookings, orders |
| `artisan@wanas.dz` | artisan | Publishing a product with an AI-drafted story |
| `office@wanas.dz` | institution | The anonymised institutional dashboard |

### Without Docker

```bash
# API — needs PostgreSQL 16 with pgvector, and optionally Redis
cd api && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python -m app.seed
.venv/Scripts/python -m uvicorn app.main:app --reload
```

```bash
cd web && npm install && npm run dev
```

---

## What is here

```
api/                 FastAPI — API, RAG, recommender, planner, vision
  app/ai/            The intelligence layer, testable without a database
  app/routers/       auth · sites · guide · itineraries · bookings · marketplace · practical · dashboard
  app/seed_data/     The heritage corpus and marketplace seed, as JSON
  tests/             97 tests that need nothing running, 18 that need Postgres
web/                 Next.js 15 PWA — five locales, RTL, installable
  src/components/art/  19 inline SVG illustrations, ~5 kB total
  public/vendor/       A-Frame + AR.js + Hiro marker, vendored for offline AR
scripts/demo.ps1     One command to a running, seeded demo (.sh alongside)
docs/demo-script.md  Four-minute presenter walkthrough
docs/brd.md          Requirements this build was written against
docker-compose.yml   Postgres+pgvector, Redis, API, web
```

### The five layers of the architecture document

| Layer | Here |
|---|---|
| Client | `web/` — Next.js PWA, mobile-first at 375 px, installable |
| API gateway | FastAPI routers with JWT bearer auth |
| Application services | One router per domain, no cross-imports between them |
| Artificial intelligence | `api/app/ai/` — provider, RAG, recommender, planner, vision |
| Data | PostgreSQL + pgvector, Redis cache, JSONB for flexible fields |

---

## The parts worth reading

### Grounding

The guide may only assert what a retrieved, editorially-validated passage
supports. Retrieval is **hybrid**: a dense pass over pgvector catches paraphrase
and misspelling, a lexical pass over Postgres full-text catches proper nouns the
dense pass dilutes, and the two are fused (`api/app/ai/rag.py`). Anything scoring
under the relevance floor is dropped, and an empty passage list is a *refusal*,
never a prompt — so "I don't have that" is a designed outcome, not a failure.

Every answer returns `sources[]`, and the UI shows them.

### Provider independence

The architecture document names single-vendor LLM dependency as risk #1.
`api/app/ai/provider.py` is the only file in the codebase that knows a vendor
exists. Two implementations satisfy the same contract:

- `ClaudeProvider` — Anthropic Messages API, including multimodal identification.
- `OfflineProvider` — composes the answer from the retrieved passages. Extractive,
  never generative: it can be wrong about emphasis, never about facts.

That is also what makes the whole platform demo-able in a room with no
connectivity — a competition constraint, not a nicety. A-Frame, AR.js and the
Hiro marker are vendored under `web/public/vendor/` (about 3.1 MB, MIT, pinned
and attributed in `NOTICE.md` there), so **augmented reality works offline too**.
Nothing in WANAS reaches for a third-party host at runtime except the Google
Fonts stylesheet, which degrades to system fonts.

### Cold start

Recommendations blend content-based and collaborative filtering, and the blend
weight is a *function of how much evidence the user has produced*
(`api/app/ai/recommender.py`). A first-session visitor is served by content
alone; the collaborative share rises with interactions and is capped, so a
popular-item echo chamber cannot form.

### Language

Darija (`dz`) is a first-class locale, not a fallback for Arabic — it is the
project's stated differentiator. It has its own message bundle, its own prompt
guidance, its own heritage documents (not just phrasebook tips), and its own
answers.

**Every site is documented in both French and Arabic**, enforced by a test. That
floor exists because the alternative is the asymmetry the project was built to
remove: a French speaker getting a native passage about Constantine while an
Arabic or Darija speaker gets the same facts second-hand through French.

Arabic text is folded
(diacritics, alef and hamza carriers, ta marbuta) before both embedding and
full-text indexing, so an unvowelled Darija question matches vowelled MSA
corpus text.

Arabic and Darija render `dir="rtl"` end to end, including chat bubble corners
and chevron direction.

### Photograph identification

Two channels, in this order (`api/app/ai/vision.py`):

1. **Where the photo was taken.** EXIF GPS, or a live fix from the browser. That
   is a measurement, not a guess, and it needs no model and no network.
2. **What the photo shows.** Multimodal identification, when a key is configured,
   refining the geographic shortlist.

Below a confidence floor the endpoint reports "unidentified" and offers nearby
candidates rather than naming a monument it cannot see.

### Anonymity

The institutional dashboard never computes a cell backed by fewer than
`MIN_COHORT` distinct visitors, and it tells you what it withheld
(`api/app/routers/dashboard.py`). Week-over-week trends are suppressed when the
*prior* window is small too, because a change against a tiny baseline leaks that
baseline. The seed deliberately puts some provinces above the floor and one below
it, so you can watch suppression happen rather than take it on trust.

### Artwork

Every site and craft product is an inline SVG drawn from that subject's real
architecture or technique (`web/src/components/art/`): Tipaza's seaward
colonnade with one broken shaft, Timgad's triple-bay arch, the M'Zab's ksar in
concentric rings under a tapering minaret, Constantine's gorge with the Sidi
M'Cid deck slung across it, Kabyle chevrons on the pottery, the khomessa's
engraved palm on the silver.

Nineteen illustrations cost **about 5 kB** in the shared bundle, need no network
and carry no licensing, and because they take the app's own palette a screen
full of them reads as one system rather than a photo collage. They are
placeholders with intent, not stock art — Phase 2 replaces them with a
commissioned photography set, and only `SiteArt`/`CraftArt` change when it does.

Gradient ids are namespaced per instance with `useId()`. Several of these render
side by side, and duplicate ids would make every card paint the first card's sky.

### Money

Integer centimes DZD end to end. No float ever touches a price, a booking total
or a commission. Display strings use the Algerian convention — narrow no-break
space for thousands, comma for decimals — and that separator is a named
constant, not an invisible character inside a format string.

Stock is decremented inside the `WHERE` clause, so two buyers racing for the last
rug cannot both win.

---

## Tests

```bash
cd api && .venv/Scripts/python -m pytest -q          # 97 tests, nothing running
docker compose up -d db cache                        # then the other 18
cd api && .venv/Scripts/python -m pytest -q
```

**97 tests run with nothing running at all** — no database, no Redis, no API key.
They cover the rules that are expensive to get wrong: Arabic folding and
cross-script isolation, retrieval fusion and the refusal floor, the grounding
contract, trip parsing in French / Arabic / Darija / English, the daily travel
budget, cold-start blending, geographic confidence bands, money formatting, the
booking state machine, and k-anonymity suppression.

Forty-three of those run retrieval **over the corpus that actually ships**
(`tests/test_corpus.py`), in memory, so a bad content edit fails on a laptop.
There is one Arabic case per site, so a coverage gap fails in CI rather than in
front of a visitor, and the Darija case asserts a *margin over the best wrong
site* — an argmax that wins by a hair is hash luck, not retrieval.

A further **18 integration tests** (`tests/test_integration.py`) exercise the
paths that only exist with a real PostgreSQL — pgvector retrieval, transactional
stock, the dashboard floor over real rows. They skip with a clear reason when no
database answers, and seed the database named in `DATABASE_URL`, so point that at
a scratch database.

---

## Roadmap position

This is **Phase 1** of the dossier's three phases.

| | Status |
|---|---|
| Conversational guide, grounded, 5 languages | ✅ |
| Personalised itineraries | ✅ |
| Hybrid recommender | ✅ |
| Bookings, marketplace, reviews | ✅ |
| AR reconstruction | ✅ marker-based, 4 sites |
| Institutional dashboard | ✅ preview, k-anonymous |
| Payment capture (CIB / Edahabia) | ⬜ Phase 2 |
| Live weather, crowding, pharmacy rotas | ⬜ Phase 2 |
| Flutter native client | ⬜ Phase 2 |
| Kubernetes, nationwide corpus | ⬜ Phase 3 |

### Known limits, stated plainly

- **Embeddings are lexical, not semantic.** The default embedder is a
  deterministic hashing projection so the platform runs with no key and no cost.
  Hybrid retrieval compensates, but a neural embedder will retrieve better:
  implement `Embedder`, run `python -m app.seed --reindex`, nothing else moves.
- **AR marker tracking is unverified on a physical device.** The libraries are
  vendored and confirmed to load and register their components from our own
  origin, the marker is the genuine AR.js Hiro image, and the camera-denied path
  is confirmed to recover — but pointing a real phone at a real marker needs a
  camera, which no CI has.
- **The database-backed paths were built but not executed on the authoring
  machine**, which had no Docker engine and no local PostgreSQL. That is exactly
  what `tests/test_integration.py` is for: bring up `db` and run it, and you will
  know in about twenty seconds whether retrieval, stock and suppression behave.
- **Site photography is absent.** Every site and craft is drawn as an inline SVG
  illustration instead (see below) — deliberate placeholder art, not photographs
  of the real monuments.
- **Pharmacy rotas return empty** rather than stale — the wilaya feed is Phase 2.
- **Tokens live in `localStorage`**, which is the honest choice for a PWA on a
  different origin than the API. Phase 2 moves to same-origin httpOnly cookies.

---

Project owner: Touaibia Ahmed · IA Tour Algérie 2026
