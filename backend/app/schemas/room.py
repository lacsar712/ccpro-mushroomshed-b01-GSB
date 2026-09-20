from marshmallow import Schema, fields, validate

from app.cooldown_service import as_aware

ROOM_STATUSES = ("fruiting", "idle", "sanitize")


class RoomCreateSchema(Schema):
    shed_id = fields.Int(required=True, data_key="shedId")
    room_code = fields.Str(required=True, data_key="roomCode", validate=validate.Length(min=1, max=32))
    species = fields.Str(required=True, validate=validate.Length(min=1, max=64))
    capacity_bags = fields.Int(required=True, data_key="capacityBags", validate=validate.Range(min=1))
    status = fields.Str(required=True, validate=validate.OneOf(ROOM_STATUSES))


class RoomStatusUpdateSchema(Schema):
    status = fields.Str(required=True, validate=validate.OneOf(ROOM_STATUSES))


class RoomOutSchema(Schema):
    id = fields.Int(dump_only=True)
    shed_id = fields.Int(data_key="shedId")
    room_code = fields.Str(data_key="roomCode")
    species = fields.Str()
    capacity_bags = fields.Int(data_key="capacityBags")
    status = fields.Str()
    cool_until = fields.Method("get_cool_until", data_key="coolUntil")
    cooling = fields.Method("get_cooling")

    def get_cool_until(self, obj):
        cooldown = getattr(obj, "latest_cooldown", None)
        if cooldown is None:
            return None
        return as_aware(cooldown.cool_until).isoformat()

    def get_cooling(self, obj):
        return bool(getattr(obj, "cooling", False))
