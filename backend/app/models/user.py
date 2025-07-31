"""
User model and related schemas
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class User(Base):
    """User model - extends Supabase Auth users"""
    __tablename__ = "users"
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # Robinhood credentials (encrypted)
    robinhood_username = Column(String, nullable=True)
    robinhood_password_hash = Column(Text, nullable=True)
    robinhood_mfa_code = Column(String, nullable=True)
    
    # Preferences
    theme = Column(String, default="light")  # light/dark
    timezone = Column(String, default="America/New_York")
    currency = Column(String, default="USD")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    last_login = Column(DateTime(timezone=True), nullable=True)