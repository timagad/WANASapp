# WANAS — the four-minute demo

**One line:** WANAS answers a traveller's question in their own language,
including Darija, and never invents a fact about Algerian heritage.

This is a beat-by-beat script. Suggested spoken lines are in French; swap to
Arabic or Darija if that suits the room better — the app follows either way, and
switching language *in front of the jury* is itself one of the strongest moments.

---

## Before you start (5 minutes, not during the demo)

```powershell
.\scripts\demo.ps1
```

That brings everything up and waits until it genuinely answers. Then:

- [ ] Open **http://localhost:3000** and let every screen load once, so nothing
      is fetching while you present.
- [ ] Sign in as `visiteur@wanas.dz` / `wanas-demo-2026`.
- [ ] Have the **marker** ready: open the AR screen, tap *view the marker*, and
      either print it or show it on a second screen. 30–50 cm from the phone.
- [ ] Decide your closing line and rehearse only that one.

**If you have no internet in the room, change nothing.** The whole platform runs
offline, AR included. That is a feature you should point at, not a risk you
should hide.

---

## 0:00 — 0:30 · The problem

> « L'Algérie a sept sites classés au patrimoine mondial. Le problème n'est pas
> le patrimoine — c'est que l'information est éparpillée, souvent fausse, et
> presque jamais dans la langue du visiteur. »

Open the app on the home screen. Don't narrate the interface; let it sit there
while you say the sentence.

---

## 0:30 — 1:30 · The guide, and the thing nobody else does

Go to **Guide**. Type a question **in Darija**:

```
وين تيبازة وواش كاين فيها
```

While it answers:

> « Je viens de poser la question en darija — pas en arabe classique, en darija.
> C'est la langue dans laquelle les Algériens parlent réellement. »

When the answer appears, **open the Sources panel** underneath it.

> « Et voici ce qui compte le plus : chaque réponse cite ses sources. WANAS ne
> répond que sur la base d'une documentation validée. Il ne devine pas. »

**Then do this** — it is the strongest thirty seconds in the demo. Ask something
Algeria's heritage base cannot answer:

```
Quel est le cours de clôture du Nasdaq hier ?
```

> « Il dit qu'il ne sait pas. Un guide touristique qui invente une date ou un
> siècle, c'est pire que pas de guide du tout. Refuser de répondre, c'est une
> décision de conception. »

---

## 1:30 — 2:15 · One sentence becomes a real trip

Go to **Itinéraire**. Type, in plain language:

```
3 jours à Alger avec mes parents, entre histoire et détente
```

Point at three things in the result, quickly:

1. **Trois jours** — it read the duration.
2. **« Mobilité réduite prise en compte »** — it understood *mes parents* and
   dropped the sites with difficult ground.
3. The **hours and travel distance** — no day sends a family across the country.

> « Personne n'a rempli un formulaire. Une phrase, et le programme existe. »

---

## 2:15 — 2:45 · Standing a ruin back up

On a Tipaza, Timgad, Djémila or Qal'a stop, tap **Voir en réalité augmentée**.
Allow the camera, point at the marker.

> « Le visiteur est devant des ruines. Là, il voit le monument tel qu'il était. »

Let the reconstruction turn once. Don't over-explain it — it explains itself.

---

## 2:45 — 3:15 · The artisan gets paid

Go to **Artisanat**, open the Kabyle pottery.

> « Chaque pièce arrive avec sa technique, sa région, et l'histoire de l'artisan
> — pas une fiche produit générique. L'artisan gagne une vitrine ; le visiteur
> repart avec un objet dont il connaît l'origine. »

---

## 3:15 — 3:45 · What the State gets out of it

Sign in as `office@wanas.dz` and open **Tableau de bord institutionnel**.

Point at the **Données masquées** section:

> « Regardez ce que le tableau refuse d'afficher. Toute donnée qui concerne trop
> peu de visiteurs est retirée — pas arrondie, retirée. Un office du tourisme
> obtient des tendances réelles, sans qu'aucun individu ne soit identifiable. »

---

## 3:45 — 4:00 · Close

Switch the language to **العربية** in the profile. The interface flips
right-to-left in front of them.

> « Une seule application. Cinq langues, dont la darija. Et tout ce que vous
> venez de voir fonctionne sans connexion internet. »

Stop talking there.

---

## If something goes wrong

| What happens | What to do |
|---|---|
| The guide is slow | You are on the Claude path and the network is poor. Say so and keep going — or remove the API key beforehand and run offline, which is instant. |
| The camera is refused | The recovery screen explains it. Say *« la caméra exige une connexion sécurisée »*, show the marker image instead, and move on. Do not debug on stage. |
| A screen shows the API warning | The API stopped. `docker compose restart api`, wait fifteen seconds. Keep talking about the architecture while it comes back. |
| AR does not find the marker | Move the phone to 30–50 cm and steady it. If it does not catch within ten seconds, move on — it is one beat of four minutes, not the demo. |

---

## The three sentences to leave them with

1. It answers in **Darija**, which no international tool does.
2. It **cites its sources**, and refuses when it has none.
3. It works with **no internet**, which is the reality of many Algerian tourist
   sites.
