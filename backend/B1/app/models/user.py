from sqlalchemy import Column, String, Integer, DateTime, JSON
from app.database import Base
from datetime import datetime, timezone

def utcnow():
    return datetime.now(timezone.utc)

class UserPreference(Base):
    __tablename__ = "user_preferences"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(String, unique=True, index=True)
    partner_id  = Column(String, nullable=True)
    mood        = Column(String)
    food_type   = Column(JSON, default=list)
    budget      = Column(Integer)
    avoid       = Column(String, nullable=True)
    age_group   = Column(String, nullable=True)
    created_at  = Column(DateTime, default=utcnow)
    updated_at  = Column(DateTime, default=utcnow, onupdate=utcnow)