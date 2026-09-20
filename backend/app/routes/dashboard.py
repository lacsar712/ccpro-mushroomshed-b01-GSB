from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import func

from app.database import SessionLocal
from app.cooling import is_cooling, latest_cooldown_map, now_utc
from app.models.climate_log import ClimateLog
from app.models.flush_harvest import FlushHarvest
from app.models.room import Room
from app.models.shed import Shed
from app.schemas.dashboard import DashboardCoolingSchema, DashboardStatsSchema

bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")

stats_schema = DashboardStatsSchema()
cooling_schema = DashboardCoolingSchema()


@bp.get("/stats")
@jwt_required()
def get_stats():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        shed_total = db.query(func.count(Shed.id)).scalar() or 0
        fruiting_room_count = (
            db.query(func.count(Room.id)).filter(Room.status == "fruiting").scalar() or 0
        )
        climate_last_24h = (
            db.query(func.count(ClimateLog.id))
            .filter(ClimateLog.recorded_at >= now - timedelta(hours=24))
            .scalar()
            or 0
        )
        harvest_kg_last_7d = (
            db.query(func.coalesce(func.sum(FlushHarvest.weight_kg), 0.0))
            .filter(FlushHarvest.harvested_at >= now - timedelta(days=7))
            .scalar()
            or 0.0
        )
        payload = {
            "shed_total": shed_total,
            "fruiting_room_count": fruiting_room_count,
            "climate_last_24h": climate_last_24h,
            "harvest_kg_last_7d": float(harvest_kg_last_7d),
        }
        return jsonify(stats_schema.dump(payload))
    finally:
        db.close()


@bp.get("/cooling")
@jwt_required()
def get_cooling():
    """冷却中的出菇室统计；cooling 判定与 GET /api/rooms 共用同一份规则。"""
    db = SessionLocal()
    try:
        now = now_utc()
        rooms = db.query(Room).order_by(Room.id).all()
        cd_map = latest_cooldown_map(db, [r.id for r in rooms])
        sheds = {s.id: s for s in db.query(Shed).all()}
        total = 0
        counts: dict[int, int] = {}
        for room in rooms:
            if is_cooling(cd_map.get(room.id), now):
                total += 1
                counts[room.shed_id] = counts.get(room.shed_id, 0) + 1
        by_shed = [
            {
                "shed_id": shed_id,
                "shed_name": sheds[shed_id].name if shed_id in sheds else None,
                "count": count,
            }
            for shed_id, count in sorted(counts.items())
        ]
        return jsonify(cooling_schema.dump({"total": total, "by_shed": by_shed}))
    finally:
        db.close()
