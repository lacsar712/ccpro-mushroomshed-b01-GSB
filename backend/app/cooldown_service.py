from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, Optional

from sqlalchemy import func

from app.models.cooldown import COOLDOWN_HOURS, Cooldown
from app.models.room import Room


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_aware(dt: Optional[datetime]) -> Optional[datetime]:
    # MySQL 的 DATETIME 不保留时区，读回为 naive，统一按 UTC 处理。
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def is_cooling(cooldown: Optional[Cooldown], now: datetime) -> bool:
    """未到 coolUntil 且未豁免即为冷却中。"""
    if cooldown is None or cooldown.waived_at is not None:
        return False
    return as_aware(cooldown.cool_until) > now


def open_cooldown(room_id: int, left_at: Optional[datetime] = None) -> Cooldown:
    left_at = left_at or utcnow()
    return Cooldown(
        room_id=room_id,
        left_at=left_at,
        cool_until=left_at + timedelta(hours=COOLDOWN_HOURS),
    )


def latest_cooldowns(
    db, room_ids: Optional[Iterable[int]] = None
) -> Dict[int, Cooldown]:
    """每个室最近一次冷却记录，单查询取回。"""
    latest_id_subq = db.query(func.max(Cooldown.id)).group_by(Cooldown.room_id)
    if room_ids is not None:
        latest_id_subq = latest_id_subq.filter(Cooldown.room_id.in_(list(room_ids)))
    rows = db.query(Cooldown).filter(Cooldown.id.in_(latest_id_subq)).all()
    return {cd.room_id: cd for cd in rows}


def enrich_rooms(db, rooms: list[Room], now: Optional[datetime] = None) -> list[Room]:
    """在 Room 对象上挂最近冷却记录与 cooling 标记，供序列化使用。"""
    now = now or utcnow()
    if rooms:
        latest = latest_cooldowns(db, [r.id for r in rooms])
    else:
        latest = {}
    for room in rooms:
        cooldown = latest.get(room.id)
        room.latest_cooldown = cooldown  # type: ignore[attr-defined]
        room.cooling = is_cooling(cooldown, now)  # type: ignore[attr-defined]
    return rooms


def cooling_summary(db, now: Optional[datetime] = None) -> dict:
    """一次性算出 cooling 明细，total 与 byShed 均出自同一份判定结果。"""
    now = now or utcnow()
    rooms = db.query(Room.id, Room.shed_id).order_by(Room.id).all()
    latest = latest_cooldowns(db, [r.id for r in rooms])
    by_shed: Dict[int, int] = {}
    for room in rooms:
        if is_cooling(latest.get(room.id), now):
            by_shed[room.shed_id] = by_shed.get(room.shed_id, 0) + 1
    return {"total": sum(by_shed.values()), "by_shed": by_shed}
