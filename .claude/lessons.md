# Lessons — WANAS
Last pruned: 06/09/2026

## Active lessons
- Ground every heritage claim in a retrieved corpus chunk before it reaches the user. Why: the dossier names factual error as the top adoption risk for an AI guide about national heritage; an ungrounded answer is worse than no answer. Applies to: any change in `api/app/ai/`.
- Keep the LLM behind `provider.py` and never import an SDK anywhere else. Why: the architecture doc lists single-vendor dependency as risk #1 and names the abstraction layer as the mitigation. Applies to: any new AI feature.
- Money is integer centimes DZD end to end. Why: floats silently corrupt totals and commissions. Applies to: bookings, marketplace, dashboard.
- Darija (`dz`) is a first-class locale, not an Arabic dialect fallback. Why: Darija support is the project's stated differentiator against generic international tools. Applies to: i18n, prompts, seed content.
- The whole platform must demo with zero network. Why: a competition jury room cannot be assumed to have connectivity or a funded API key. Applies to: any new external dependency.
- Namespace hashed embedding features by writing system. Why: without it an Arabic question out-scored the correct Arabic passage against an unrelated French one on pure hash collision — the tuning knobs could not have fixed it. Applies to: `api/app/ai/embeddings.py`.
- Test retrieval on the shipped corpus, not only on synthetic strings, and assert a margin rather than an argmax. Why: the Darija regression was invisible to the synthetic tests and a bare argmax can pass on hash luck. Applies to: `api/tests/test_corpus.py`.
- Fold keywords through `normalize()` wherever they are compared to folded text. Why: `_detect_party` compared raw Arabic keywords against normalised input, so "العائلة" silently stopped matching and every Darija family trip was planned for one person. Applies to: `api/app/ai/planner.py`.
- Spell out invisible characters as named constants. Why: a U+202F thousands separator sat inside a format string and read as a plain space in review; three tests failed before anyone could see why. Applies to: any formatting code.
- Never run `npm run build` while `next dev` is live on the same tree. Why: the production build overwrites `.next/`, the dev server's chunk manifest goes stale, and every route starts 500ing with `Cannot find module './403.js'` — which reads like an app bug and is not one. Applies to: any verification pass on the web app.
- Namespace SVG gradient/filter ids per instance with `useId()`. Why: repeated inline SVGs share a document, so a fixed id makes every copy reference the first one's gradient. Applies to: anything in `web/src/components/art/`.
- Check illustrations at their real rendered size before calling them done. Why: four of nineteen looked fine as thumbnails and were unreadable at card size — floating columns, a minaret that read as an office block, white houses on a white sky. Applies to: any generated artwork.
- Measure a retrieval margin against the best *wrong* answer, not the runner-up. Why: adding a second Tipaza document made the runner-up another correct Tipaza passage, so the margin test failed for the good reason that coverage improved. Applies to: any ranking assertion.
- Set `response_model=None` on 204 routes. Why: FastAPI infers a response model from the `-> None` return annotation and asserts at import time, so the whole app fails to start. Applies to: any new no-content endpoint.

## Archived lessons
_(none yet)_
