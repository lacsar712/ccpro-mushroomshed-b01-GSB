from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError

from app.cooldown_service import as_aware, utcnow
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
        if not user or user.role != "admin":
            return jsonify({"detail": "仅管理员可豁免冷却"}), 403

        try:
            data = waive_schema.load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return validation_error_response(err)

        reason = data["reason"].strip()
        if len(reason) < 4:
            return jsonify({"detail": "reason 去掉空白后至少 4 个字"}), 400

        cooldown = db.query(Cooldown).filter(Cooldown.id == cooldown_id).first()
        if not cooldown:
            return jsonify({"detail": "冷却记录不存在"}), 404
        if cooldown.waived_at is not None:
            return jsonify({"detail": "该冷却已豁免"}), 400

        cooldown.waived_at = utcnow()
        cooldown.waive_reason = reason
        db.commit()
        db.refresh(cooldown)
        return jsonify(out_schema.dump(cooldown))
    finally:
        db.close()
