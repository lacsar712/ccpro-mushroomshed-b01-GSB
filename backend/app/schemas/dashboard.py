from marshmallow import Schema, fields


class DashboardStatsSchema(Schema):
    shed_total = fields.Int(data_key="shedTotal")
    fruiting_room_count = fields.Int(data_key="fruitingRoomCount")
    climate_last_24h = fields.Int(data_key="climateLast24h")
    harvest_kg_last_7d = fields.Float(data_key="harvestKgLast7d")


class ShedCoolingSchema(Schema):
    shed_id = fields.Int(data_key="shedId")
    shed_name = fields.Str(data_key="shedName")
    cooling = fields.Int()


class DashboardCoolingSchema(Schema):
    total = fields.Int()
    by_shed = fields.List(fields.Nested(ShedCoolingSchema), data_key="byShed")
