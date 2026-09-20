from marshmallow import Schema, fields, validates, ValidationError


class CooldownOutSchema(Schema):
    id = fields.Int(dump_only=True)
    room_id = fields.Int(data_key="roomId")
    left_at = fields.DateTime(data_key="leftAt")
    cool_until = fields.DateTime(data_key="coolUntil")
    waived_at = fields.DateTime(allow_none=True, data_key="waivedAt")
    waive_reason = fields.Str(allow_none=True, data_key="waiveReason")


class CooldownWaiveSchema(Schema):
    reason = fields.Str(required=True)

    @validates("reason")
    def _reason_min_len(self, value, **kwargs):
        if len(value.strip()) < 4:
            raise ValidationError("reason 去除空白后至少 4 个字")
