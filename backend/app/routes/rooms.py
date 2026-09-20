from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.cooldown_service import as_aware, enrich_rooms, is_cooling, latest_cooldowns, open_cooldown, utcnow
from app.database import SessionLocal
from app.models.room import Room
from app.models.shed import Shed
from app.schemas.room import RoomCreateSchema, RoomOutSchema, RoomStatusUpdateSchema
from app.utils import validation_error_response

bp = Blueprint("rooms", __name__, url_prefix="/api/rooms")

create_schema = RoomCreateSchema()
status_schema = RoomStatusUpdateSchema()
out_schema = RoomOutSchema()
out_many = RoomOutSchema(many=True)


@bp.get("")
@jwt_required()
def list_rooms():
    db = SessionLocal()
    try:
        shed_id = request.args.get("shedId", type=int)
        q = db.query(Room)
        if shed_id is not None:
            q = q.filter(Room.shed_id == shed_id)
        rows = q.order_by(Room.id).all()
        enrich_rooms(db, rows, now=utcnow())
        return jsonify(out_many.dump(rows))
    finally:
        db.close()


@bp.post("")
@jwt_required()
def create_room():
    db = SessionLocal()
    try:
        try:
            data = create_schema.load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return validation_error_response(err)
        shed = db.query(Shed).filter(Shed.id == data["shed_id"]).first()
        if not shed:
            return jsonify({"detail": "菇房不存在"}), 400
        item = Room(
            shed_id=data["shed_id"],
            room_code=data["room_code"],
            species=data["species"],
            capacity_bags=data["capacity_bags"],
            status=data["status"],
        )
        db.add(item)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return jsonify({"detail": "同菇房内出菇室编号已存在"}), 400
        db.refresh(item)
        enrich_rooms(db, [item], now=utcnow())
        return jsonify(out_schema.dump(item)), 201
    finally:
        db.close()


@bp.patch("/<int:room_id>/status")
@jwt_required()
def update_room_status(room_id: int):
    db = SessionLocal()
    try:
        try:
            data = status_schema.load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return validation_error_response(err)

        room = db.query(Room).filter(Room.id == room_id).first()
        if not room:
            return jsonify({"detail": "出菇室不存在"}), 404

        new_status = data["status"]
        now = utcnow()

        if new_status == "fruiting" and room.status != "fruiting":
            latest = latest_cooldowns(db, [room.id]).get(room.id)
            if is_cooling(latest, now):
                return (
                    jsonify(
                        {
                            "detail": "冷却未结束，不能写回 fruiting",
                            "coolUntil": as_aware(latest.cool_until).isoformat(),
                        }
                    ),
                    409,
                )

        # 离开 fruiting 的那一刻登记一轮 36 小时冷却。
        if room.status == "fruiting" and new_status != "fruiting":
            db.add(open_cooldown(room.id, left_at=now))

        room.status = new_status
        db.commit()
        db.refresh(room)
        enrich_rooms(db, [room], now=now)
        return jsonify(out_schema.dump(room))
    finally:
        db.close()


@bp.delete("/<int:room_id>")
@jwt_required()
def delete_room(room_id: int):
    db = SessionLocal()
    try:
        item = db.query(Room).filter(Room.id == room_id).first()
        if not item:
            return jsonify({"detail": "出菇室不存在"}), 404
        db.delete(item)
        db.commit()
        return "", 204
    finally:
        db.close()
