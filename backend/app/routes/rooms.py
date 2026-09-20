from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.cooling import (
    cool_until_for,
    is_cooling,
    iso_utc,
    latest_cooldown_map,
    now_utc,
)
from app.database import SessionLocal
from app.models.cooldown import Cooldown
from app.models.room import Room
from app.models.shed import Shed
from app.schemas.room import RoomCreateSchema, RoomOutSchema, RoomStatusUpdateSchema
from app.utils import validation_error_response

bp = Blueprint("rooms", __name__, url_prefix="/api/rooms")

create_schema = RoomCreateSchema()
status_schema = RoomStatusUpdateSchema()
out_schema = RoomOutSchema()


def room_row(room: Room, cooldown, now) -> dict:
    """列表/详情共用的行形状：基础字段 + coolUntil、cooling、cooldownId。"""
    row = out_schema.dump(room)
    row["coolUntil"] = iso_utc(cooldown.cool_until) if cooldown else None
    row["cooling"] = is_cooling(cooldown, now)
    row["cooldownId"] = cooldown.id if cooldown else None
    return row


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
        now = now_utc()
        cd_map = latest_cooldown_map(db, [r.id for r in rows])
        return jsonify([room_row(r, cd_map.get(r.id), now) for r in rows])
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
        return jsonify(room_row(item, None, now_utc())), 201
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
        now = now_utc()
        if new_status == room.status:
            cd = latest_cooldown_map(db, [room.id]).get(room.id)
            return jsonify(room_row(room, cd, now))

        if room.status == "fruiting":
            # 离开 fruiting：登记冷却，coolUntil = leftAt + 36h
            cd = Cooldown(room_id=room.id, left_at=now, cool_until=cool_until_for(now))
            db.add(cd)
            room.status = new_status
            db.commit()
            db.refresh(cd)
            return jsonify(room_row(room, cd, now))

        cd = latest_cooldown_map(db, [room.id]).get(room.id)
        if new_status == "fruiting" and is_cooling(cd, now):
            # 未到点且未豁免：409，正文带 coolUntil，status 保持不动
            return jsonify(
                {
                    "detail": "出菇室仍在冷却，未到 coolUntil 且未豁免，不能回到 fruiting",
                    "coolUntil": iso_utc(cd.cool_until),
                }
            ), 409
        room.status = new_status
        db.commit()
        return jsonify(room_row(room, cd, now))
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
