# WANAS — Business Requirements Document (Phase 1 MVP)

**Source of truth:** `WANAS_Project_Dossier_EN_2.md` (product) + `WANAS_Architecture_Technique_EN.md` (technical).
**Owner:** Touaibia Ahmed · **Context:** IA Tour Algérie 2026 · **Scope:** Phase 1 MVP (0–3 months), pilot provinces Algiers / Tipaza / Ghardaïa.

---

## 1. Verdict

WANAS is one app that answers a traveller's question in their own language — including Algerian Darija — and turns the answer into a real itinerary, a real booking, and a real purchase from a real artisan. Phase 1 proves the hard part: an AI guide that never invents facts about Algerian heritage.

## 2. Users

| Persona | Need | Phase 1 |
|---|---|---|
| Foreign tourist | Reliable, multilingual guidance | ✅ |
| Domestic tourist | Discover other provinces | ✅ |
| Diaspora visitor | Reconnect with heritage, Darija | ✅ |
| Artisan / guide (partner) | Digital visibility, income | ✅ listing + orders |
| Tourism office | Aggregated, anonymised trends | ✅ preview dashboard |

## 3. Epics and stories

### E1 — AI conversational guide
- **S1.1** As a visitor I ask a free-text question in ar / dz / kab / fr / en and get a grounded answer.
  - AC-1.1 Every factual answer cites at least one heritage source, returned to the client as `sources[]`.
  - AC-1.2 If retrieval returns nothing above the relevance floor, the guide says it does not know instead of inventing.
  - AC-1.3 Answer language matches the request language; Darija requests get Darija answers.
  - AC-1.4 Round trip < 5 s p95 with a live LLM; < 300 ms with the offline provider.
- **S1.2** As a visitor with no connectivity I still get useful answers.
  - AC-1.5 With no `ANTHROPIC_API_KEY`, the guide answers from retrieved corpus extracts and labels itself `offline`.
- **S1.3** As a visitor I photograph a monument and get its story.
  - AC-1.6 `POST /ai/vision` accepts an image and returns a ranked site match with confidence and narrative.

### E2 — Personalised itineraries
- **S2.1** As a visitor I describe my trip in one sentence and get a day-by-day itinerary.
  - AC-2.1 Itinerary respects duration, party size, budget band, mobility constraint and interests.
  - AC-2.2 Every stop carries arrival time, dwell minutes, and a practical tip.
  - AC-2.3 Stops are geographically coherent — no day exceeds the configured travel budget.
- **S2.2** As a visitor I save, reload and adjust my itinerary.
  - AC-2.4 Itineraries persist per user and are re-fetchable by id.

### E3 — Recommendations
- **S3.1** As a visitor I see sites suited to me, even on my first session.
  - AC-3.1 Hybrid score = content-based + collaborative, weighted; cold-start falls back to content-only without error.
  - AC-3.2 Recommendations exclude sites already in the user's active itinerary.

### E4 — Bookings and practical services
- **S4.1** As a visitor I book a certified guide, a stay or an activity.
  - AC-4.1 Booking transitions `pending → confirmed → cancelled|completed`; illegal transitions are rejected.
  - AC-4.2 Amounts are stored in integer centimes DZD; no floats in money paths.
- **S4.2** As a visitor I get practical info for my location (transport, emergency numbers, on-duty pharmacies).

### E5 — Heritage immersion (AR)
- **S5.1** As a visitor at a ruined site I point my camera and see the monument reconstructed.
  - AC-5.1 AR route is reachable from the site sheet and from the itinerary stop.
  - AC-5.2 Camera-denied and non-HTTPS cases show a recovery screen, never a blank page.
- **S5.2** Narrative depth adapts to `child | standard | expert`.

### E6 — Crafts marketplace
- **S6.1** As a visitor I browse artisan products and buy one.
  - AC-6.1 Each product shows origin, technique and the artisan's story.
  - AC-6.2 Orders decrement stock atomically; overselling is impossible.
- **S6.2** As an artisan I publish a product and AI drafts its story from my notes.

### E7 — Institutional dashboard (Phase 3 preview)
- **S7.1** As a tourism office I see aggregated trends.
  - AC-7.1 No endpoint returns a cohort smaller than `MIN_COHORT` (k-anonymity); no user id ever leaves the aggregate.

## 4. Non-functional requirements

- **NFR-1 Multilingual + RTL.** ar and dz render `dir="rtl"`; fr / en / kab LTR. Tested at 375 px.
- **NFR-2 MENA defaults.** DZD currency, DD/MM/YYYY dates, Friday–Saturday weekend, no alcohol imagery.
- **NFR-3 Security.** TLS in transit, argon2/bcrypt password hashing, short-lived JWT + refresh, no secret in the repo.
- **NFR-4 Provider independence.** Swapping the LLM vendor touches one module (`app/ai/provider.py`).
- **NFR-5 Grounding.** No heritage claim reaches the user without a corpus citation.
- **NFR-6 Offline degradation.** The whole app is demo-able with zero external network access.
- **NFR-7 Cost control.** Frequent answers cached in Redis; per-account quotas on AI calls.

## 5. Out of scope for Phase 1

Real payment capture (CIB / Edahabia), Flutter native client, Kubernetes, nationwide coverage, artisan payouts, live weather/crowding feeds.

## 6. Definition of done

Docker Compose up → seeded corpus → guide answers a Darija question with citations → itinerary generated and saved → booking created → order placed → AR scene loads → `pytest` green → dashboard refuses a sub-threshold cohort.
