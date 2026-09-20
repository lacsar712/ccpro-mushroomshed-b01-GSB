from marshmallow import Schema, fields, validate

from app.cooldown_service import as_aware


class CooldownWaiveSchema(Schema):
    reason = fields.Str(required=True, validate=validate.Length(min=1))


class CooldownOutSchema(Schema):
    id = fields.Int(dump_only=True)
    room_id = fields.Int(data_key="roomId")
    left_at = fields.Method("get_left_at", data_key="leftAt")
    cool_until = fields.Method("get_cool_until", data_key="coolUntil")
    waived_at = fields.Method("get_waived_at", data_key="waivedAt")
    waive_reason = fields.Str(allow_none=True, data_key="waiveReason")

    def get_left_at(self, obj):
        return as_aware(obj.left_at).isoformat()

    def get_cool_until(self, obj):
        return as_aware(obj.cool_until).isoformat()

    def get_waived_at(self, obj):
        if obj.waived_at is None:
            return None
        return as_aware(obj.waived_at).isoformat()
