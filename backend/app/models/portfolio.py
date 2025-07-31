"""
Portfolio model for storing portfolio snapshots
"""

from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class Portfolio(Base):
    """Portfolio snapshot model"""
    __tablename__ = "portfolios"
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    
    # Portfolio metrics
    total_value = Column(Numeric(precision=12, scale=2), nullable=True)
    total_return = Column(Numeric(precision=12, scale=2), nullable=True)
    total_return_percent = Column(Numeric(precision=8, scale=4), nullable=True)
    day_return = Column(Numeric(precision=12, scale=2), nullable=True)
    day_return_percent = Column(Numeric(precision=8, scale=4), nullable=True)
    
    # Breakdown
    stocks_value = Column(Numeric(precision=12, scale=2), nullable=True)
    options_value = Column(Numeric(precision=12, scale=2), nullable=True)
    cash_value = Column(Numeric(precision=12, scale=2), nullable=True)
    
    # Raw data from Robinhood
    raw_data = Column(JSONB, nullable=True)
    
    # Timestamps
    snapshot_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="portfolios")


# Add relationship to User model
from app.models.user import User
User.portfolios = relationship("Portfolio", back_populates="user")