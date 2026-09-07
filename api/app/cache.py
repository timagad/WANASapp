"""Redis cache and AI usage quotas.

Architecture section 10 lists AI API cost at scale as a live risk and names two
mitigations: cache frequent answers, and cap free accounts. Both live here.

Redis is treated as an accelerator, never a dependency: if it is down or absent
the platform answers exactly the same, just slower and more expensively. Losing
the cache must never lose the app.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import redis

from app.config import settings

_client: redis.Redis | None = None
_unavailable = False


def get_client() -> redis.Redis | None:
    global _client, _unavailable
    if _unavailable:
        return None
    if _client is None:
        try:
            _client = redis.Redis.from_url(
                settings.redis_url, decode_responses=True, socket_connect_timeout=1
            )
            _client.ping()
        except (redis.RedisError, OSError):
            _unavailable = True
            _client = None
    return _client


def answer_key(question: str, language: str, level: str) -> str:
    digest = hashlib.sha256(f"{language}|{level}|{question.strip().lower()}".encode()).hexdigest()
    return f"wanas:answer:{digest[:32]}"


def get_json(key: str) -> Any | None:
    client = get_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
    except redis.RedisError:
        return None
    return json.loads(raw) if raw else None


def set_json(key: str, value: Any, ttl_seconds: int) -> None:
    client = get_client()
    if client is None:
        return
    try:
        client.setex(key, ttl_seconds, json.dumps(value, ensure_ascii=False))
    except redis.RedisError:
        return


def consume_quota(identity: str, *, limit: int | None = None) -> tuple[bool, int]:
    """Count one AI call against today's allowance.

    Returns (allowed, remaining). With no cache reachable the quota cannot be
    enforced, and the call is allowed — degraded metering beats a dead guide.
    """
    limit = limit if limit is not None else settings.free_daily_ai_calls
    client = get_client()
    if client is None:
        return True, limit

    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    key = f"wanas:quota:{day}:{identity}"
    try:
        used = client.incr(key)
        if used == 1:
            client.expire(key, 60 * 60 * 26)
    except redis.RedisError:
        return True, limit
    return used <= limit, max(limit - used, 0)
