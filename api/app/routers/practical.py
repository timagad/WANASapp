"""Practical services — the unglamorous half of feeling safe in an unfamiliar
country (dossier section 5.3)."""
from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.models import TouristSite
from app.schemas import PracticalOut
from app.security import DbSession

router = APIRouter(prefix="/practical", tags=["practical"])

# National emergency numbers, identical countrywide.
EMERGENCY = {
    "all_emergencies_mobile": "112",
    "police": "17",
    "civil_protection_fire_ambulance": "14",
    "gendarmerie_nationale": "1055",
    "samu_medical": "115",
}

ETIQUETTE = {
    "fr": [
        "Le week-end algérien est vendredi et samedi : de nombreux services publics sont fermés.",
        "Demandez avant de photographier une personne, en particulier dans les médinas.",
        "Tenue couvrant les épaules et les genoux dans les mosquées et les zaouïas.",
        "Pendant le Ramadan, beaucoup de restaurants n'ouvrent qu'après le coucher du soleil.",
        "Le marchandage est normal dans les souks, courtois et sans agressivité.",
    ],
    "en": [
        "The Algerian weekend is Friday and Saturday; many public services close.",
        "Ask before photographing people, especially inside the medinas.",
        "Cover shoulders and knees in mosques and zaouias.",
        "During Ramadan many restaurants open only after sunset.",
        "Bargaining is normal in souks — friendly, never aggressive.",
    ],
    "ar": [
        "عطلة نهاية الأسبوع في الجزائر يوما الجمعة والسبت، وتغلق فيهما مرافق عمومية كثيرة.",
        "استأذن قبل تصوير الأشخاص، خاصة داخل المدن العتيقة.",
        "التزم بلباس يغطي الكتفين والركبتين في المساجد والزوايا.",
        "في رمضان لا تفتح كثير من المطاعم إلا بعد أذان المغرب.",
        "المساومة أمر معتاد في الأسواق، بلطف ومن دون إلحاح.",
    ],
    "dz": [
        "الويكاند في الجزائر الجمعة والسبت، بزاف إدارات مسكّرة.",
        "سقسي قبل ما تصوّر الناس، خاصة في القصبة والأسواق.",
        "لبس يغطّي الكتاف والركبتين كي تدخل الجامع ولا الزاوية.",
        "في رمضان أغلب المطاعم ما تحلّش حتى للفطور.",
        "التفاصل في السوق عادي، بس بالمليح.",
    ],
    "kab": [
        "Dda n Dzayer: sem n ssebt d lǧemɛa, aṭas n tmesbaniyin i imedlen.",
        "Steqsi send ad tṭṭfeḍ tugna n yemdanen.",
        "Els llebsa i yesburren tiɣmertin d yifadden deg lǧwameɛ.",
        "Deg Ramḍan, aṭas n yiṛustuṛen ldin kan seld tuɣalin n yiṭij.",
        "Ssuq: amyeḥsab ɣef ssuma d ayen yellan d annect-a.",
    ],
}


@router.get("", response_model=PracticalOut)
def practical(
    db: DbSession,
    region: str = Query(default="Alger"),
    language: str = Query(default="fr"),
) -> PracticalOut:
    known = db.execute(
        select(TouristSite.region).where(TouristSite.region == region).limit(1)
    ).scalar_one_or_none()

    return PracticalOut(
        # Echo back what we actually cover, so the client can tell an unknown
        # wilaya from a covered one instead of silently showing generic advice.
        region=known or region,
        emergency=EMERGENCY,
        transport=[
            {
                "mode": "taxi",
                "note": "Agree the fare before setting off, or ask for the meter.",
                "note_fr": "Fixez le prix avant de partir, ou demandez le compteur.",
            },
            {
                "mode": "train",
                "operator": "SNTF",
                "note": "Intercity lines serve Algiers, Oran, Constantine and Annaba.",
                "note_fr": "Lignes intervilles : Alger, Oran, Constantine, Annaba.",
            },
            {
                "mode": "metro_tram",
                "note": "Algiers has a metro and tramway; Oran, Constantine and Sétif have trams.",
                "note_fr": "Métro et tramway à Alger ; tramways à Oran, Constantine, Sétif.",
            },
        ],
        # Rotas are published by the wilaya health directorate and change nightly;
        # Phase 2 wires the live feed. Until then this is honest about being empty.
        pharmacies_on_duty=[],
        etiquette=ETIQUETTE.get(language, ETIQUETTE["fr"]),
        weekend="friday-saturday",
        currency="DZD",
    )
