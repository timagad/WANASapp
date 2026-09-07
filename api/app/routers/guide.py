"""The conversational guide — the feature the whole dossier is built around."""
from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select

from app.ai import vision as vision_ai
from app.ai.provider import RTL_LANGUAGES, get_provider
from app.ai.rag import HeritageRetriever
from app.cache import answer_key, consume_quota, get_json, set_json
from app.config import settings
from app.models import Conversation, Message, TouristSite
from app.schemas import AnswerOut, AskIn, SiteOut, SourceOut, VisionOut
from app.security import DbSession, MaybeUser

router = APIRouter(prefix="/guide", tags=["guide"])

MAX_IMAGE_BYTES = 8 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _identity(request: Request, user) -> str:
    if user is not None:
        return f"user:{user.id}"
    client = request.client.host if request.client else "anonymous"
    return f"ip:{client}"


@router.post("/ask", response_model=AnswerOut)
async def ask(payload: AskIn, request: Request, db: DbSession, user: MaybeUser) -> AnswerOut:
    allowed, remaining = consume_quota(_identity(request, user))
    if not allowed:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Daily guide allowance reached ({settings.free_daily_ai_calls}). "
            "It resets at midnight UTC.",
        )

    rtl = payload.language in RTL_LANGUAGES
    key = answer_key(payload.question, payload.language, payload.level)

    # A conversation turn depends on history, so only stateless questions are
    # served from cache.
    cacheable = payload.conversation_id is None
    if cacheable:
        cached = get_json(key)
        if cached:
            return AnswerOut(**cached, cached=True, rtl=rtl)

    passages = HeritageRetriever(db).retrieve(payload.question, language=payload.language)

    history: list[dict] = []
    conversation: Conversation | None = None
    if payload.conversation_id:
        conversation = db.get(Conversation, payload.conversation_id)
        if conversation is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
        if conversation.user_id and (user is None or conversation.user_id != user.id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your conversation")
        history = [{"role": m.role, "content": m.content} for m in conversation.messages[-6:]]

    answer = await get_provider().answer_guide(
        question=payload.question,
        passages=passages,
        language=payload.language,
        level=payload.level,
        history=history,
    )

    if conversation is None:
        conversation = Conversation(user_id=user.id if user else None, language=payload.language)
        db.add(conversation)
        db.flush()

    db.add(Message(conversation_id=conversation.id, role="user", content=payload.question))
    db.add(
        Message(
            conversation_id=conversation.id,
            role="assistant",
            content=answer.text,
            sources=answer.sources,
        )
    )
    db.commit()

    body = {
        "answer": answer.text,
        "sources": answer.sources,
        "conversation_id": conversation.id,
        "provider": answer.provider,
        "grounded": answer.grounded,
        "refused": answer.refused,
    }
    # Never cache a refusal: the corpus may gain that passage tomorrow.
    if cacheable and not answer.refused:
        set_json(key, body, settings.answer_cache_seconds)

    return AnswerOut(**body, cached=False, rtl=rtl)


@router.get("/conversations/{conversation_id}", response_model=list[dict])
def get_conversation(conversation_id: str, db: DbSession, user: MaybeUser) -> list[dict]:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    if conversation.user_id and (user is None or conversation.user_id != user.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your conversation")
    return [
        {
            "role": m.role,
            "content": m.content,
            "sources": m.sources,
            "created_at": m.created_at.isoformat(),
        }
        for m in conversation.messages
    ]


@router.post("/vision", response_model=VisionOut)
async def identify_photo(
    db: DbSession,
    user: MaybeUser,
    request: Request,
    file: UploadFile = File(...),
    language: str = Form("fr"),
    level: str = Form("standard"),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
) -> VisionOut:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Send a JPEG, PNG or WebP image"
        )
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Empty image")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Image over 8 MB")

    allowed, _ = consume_quota(_identity(request, user))
    if not allowed:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Daily guide allowance reached")

    sites = db.execute(select(TouristSite)).scalars().all()
    catalogue = [
        {
            "id": s.id,
            "slug": s.slug,
            "name": s.name,
            "region": s.region,
            "category": s.category,
            "latitude": s.latitude,
            "longitude": s.longitude,
        }
        for s in sites
    ]
    fix = (latitude, longitude) if latitude is not None and longitude is not None else None

    result = await vision_ai.identify(
        image_bytes=image_bytes,
        media_type=file.content_type,
        sites=catalogue,
        provider=get_provider(),
        language=language,
        fix=fix,
    )

    by_slug = {s.slug: s for s in sites}
    nearby = [by_slug[c["slug"]] for c in result.candidates if c["slug"] in by_slug][:4]

    if result.site_slug is None or result.site_slug not in by_slug:
        return VisionOut(
            site=None,
            confidence=0.0,
            method=result.method,
            narrative="",
            nearby=[SiteOut.of(s) for s in nearby],
        )

    site = by_slug[result.site_slug]
    passages = HeritageRetriever(db).retrieve(
        f"{site.name} {site.region} {site.category}", language=language
    )
    answer = await get_provider().answer_guide(
        question=f"Raconte l'histoire de {site.name}.",
        passages=passages,
        language=language,
        level=level,
    )
    return VisionOut(
        site=SiteOut.of(site),
        confidence=round(result.confidence, 3),
        method=result.method,
        narrative=answer.text,
        sources=[SourceOut(**s) for s in answer.sources],
        nearby=[SiteOut.of(s) for s in nearby if s.slug != site.slug],
    )
