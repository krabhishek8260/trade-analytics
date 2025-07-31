"""
Stock position model
"""

from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class StockPosition(Base):
    """Stock position model"""
    __tablename__ = "stock_positions"
    
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
    
    # Stock information
    symbol = Column(String(10), nullable=False, index=True)
    company_name = Column(String, nullable=True)
    
    # Position details
    quantity = Column(Numeric(precision=12, scale=4), nullable=False)
    average_buy_price = Column(Numeric(precision=12, scale=4), nullable=True)
    current_price = Column(Numeric(precision=12, scale=4), nullable=True)
    
    # Financial metrics
    market_value = Column(Numeric(precision=12, scale=2), nullable=True)
    total_cost = Column(Numeric(precision=12, scale=2), nullable=True)
    total_return = Column(Numeric(precision=12, scale=2), nullable=True)
    total_return_percent = Column(Numeric(precision=8, scale=4), nullable=True)
    day_return = Column(Numeric(precision=12, scale=2), nullable=True)
    day_return_percent = Column(Numeric(precision=8, scale=4), nullable=True)
    
    # Additional data
    sector = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    pe_ratio = Column(Numeric(precision=8, scale=2), nullable=True)
    market_cap = Column(Numeric(precision=15, scale=2), nullable=True)
    
    # Raw data from Robinhood
    raw_data = Column(JSONB, nullable=True)
    
    # Timestamps
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    user = relationship("User")


# Add index for efficient queries
from sqlalchemy import Index
Index("idx_stock_positions_user_symbol", StockPosition.user_id, StockPosition.symbol)