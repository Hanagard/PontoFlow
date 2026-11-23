"""MongoDB-backed fixed-window rate limiting shared by all application instances."""

import hashlib
from datetime import timedelta

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from lib.db import db
from lib.timeutil import now_utc


def _bucket_id(namespace: str, identity: str, window_seconds: int, now) -> str:
    bucket = int(now.timestamp() // window_seconds)
    raw = f"{namespace}:{identity}:{bucket}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


async def is_rate_limited(namespace: str, identity: str, limit: int, window_seconds: int) -> bool:
    now = now_utc()
    key = _bucket_id(namespace, identity, window_seconds, now)
    update = {
        "$inc": {"attempts": 1},
        "$setOnInsert": {"created_at": now, "expires_at": now + timedelta(seconds=window_seconds * 2)},
    }
    try:
        record = await db.rate_limits.find_one_and_update(
            {"_id": key}, update, upsert=True, return_document=ReturnDocument.AFTER
        )
    except DuplicateKeyError:
        record = await db.rate_limits.find_one_and_update(
            {"_id": key}, {"$inc": {"attempts": 1}}, return_document=ReturnDocument.AFTER
        )
    return bool(record and record.get("attempts", 0) > limit)


async def clear_rate_limit(namespace: str, identity: str, window_seconds: int) -> None:
    now = now_utc()
    key = _bucket_id(namespace, identity, window_seconds, now)
    await db.rate_limits.delete_one({"_id": key})
