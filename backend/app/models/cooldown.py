from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

COOLDOWN_HOURS = 36


class Cooldown(Base):
    __tablename__ = "cooldowns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), nullable=False, index=True)
    left_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cool_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    waived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    waive_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    room: Mapped["Room"] = relationship("Room", back_populates="cooldowns")
