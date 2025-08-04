from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.sql import func

from ..db.base import Base


class AppSetting(Base):
    __tablename__ = "app_settings"
    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
