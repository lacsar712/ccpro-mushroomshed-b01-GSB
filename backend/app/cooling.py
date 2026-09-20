"""出菇室冷却（Cooldown）共享判定逻辑。

GET /api/rooms 的 cooling 标记与 GET /api/dashboard/cooling 的统计
必须走同一份规则，两处分开各算各的不算数。
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, Optional

from app.models.cooldown import Cooldown

COOLDOWN_HOURS = 36


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def cool_until_for(left_at: datetime) -> datetime:
    """coolUntil = leftAt + 36 小时。"""
    return left_at + timedelta(hours=COOLDOWN_HOURS)


def _as_utc(dt: datetime) -> datetime:
    # MySQL DATETIME 读回为 naive；统一按 UTC 处理再比较
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def iso_utc(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return _as_utc(dt).isoformat()


def is_cooling(cooldown: Optional[Cooldown], now: datetime) -> bool:
    """cooling 为真 = 未到 coolUntil 且未豁免。"""
    if cooldown is None or cooldown.waived_at is not None:
        return False
    return _as_utc(cooldown.cool_until) > _as_utc(now)


def latest_cooldown_map(db, room_ids: Optional[Iterable[int]] = None) -> Dict[int, Cooldown]:
    """每个出菇室最新一条 Cooldown：{room_id: Cooldown}。"""
    q = db.query(Cooldown)
    if room_ids is not None:
        room_ids = list(room_ids)
        if not room_ids:
            return {}
        q = q.filter(Cooldown.room_id.in_(room_ids))
    rows = q.order_by(Cooldown.room_id, Cooldown.left_at.desc(), Cooldown.id.desc()).all()
    latest: Dict[int, Cooldown] = {}
    for cd in rows:
        if cd.room_id not in latest:
            latest[cd.room_id] = cd
    return latest
