from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError

from app.cooling import now_utc
from app.database import SessionLocal
from app.models.cooldown import Cooldown
from app.models.user import User
from app.schemas.cooldown import CooldownOutSchema, CooldownWaiveSchema
from app.utils import validation_error_response

bp = Blueprint("cooldowns", __name__, url_prefix="/api/cooldowns")

waive_schema = CooldownWaiveSchema()
out_schema = CooldownOutSchema()


@bp.post("/<int:cooldown_id>/waive")
@jwt_required()
def waive_cooldown(cooldown_id: int):
    db = SessionLocal()
    try:
        username = get_jwt_identity()
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return jsonify({"detail": "无效或过期的令牌"}), 401
        if user.role != "admin":
            return jsonify({"detail": "仅场长（admin）可豁免冷却"}), 403
        try:
            data = waive_schema.load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return validation_error_response(err)
        item = db.query(Cooldown).filter(Cooldown.id == cooldown_id).first()
        if not item:
            return jsonify({"detail": "冷却记录不存在"}), 404
        item.waived_at = now_utc()
        item.waive_reason = data["reason"].strip()
        db.commit()
        db.refresh(item)
        return jsonify(out_schema.dump(item))
    finally:
        db.close()
