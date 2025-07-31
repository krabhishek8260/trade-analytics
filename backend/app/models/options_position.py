"""
Options position model with enhanced analysis
"""

from sqlalchemy import Column, String, DateTime, Numeric, Integer, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class OptionsPosition(Base):
    """Options position model"""
    __tablename__ = "options_positions"
    
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
    
    # Option contract details
    underlying_symbol = Column(String(10), nullable=False, index=True)
    option_type = Column(String(4), nullable=False)  # call/put
    strike_price = Column(Numeric(precision=12, scale=4), nullable=False)
    expiration_date = Column(Date, nullable=False)
    
    # Position details
    quantity = Column(Numeric(precision=12, scale=4), nullable=False)
    contracts = Column(Integer, nullable=False)
    
    # Transaction details
    transaction_side = Column(String(4), nullable=False)  # buy/sell
    position_effect = Column(String(5), nullable=False)   # open/close
    direction = Column(String(6), nullable=False)         # credit/debit
    
    # Strategy classification
    strategy = Column(String(20), nullable=True)  # LONG CALL, SHORT PUT, etc.
    strategy_type = Column(String(20), nullable=True)  # single_leg, spread, etc.
    
    # Pricing
    average_price = Column(Numeric(precision=12, scale=4), nullable=True)
    current_price = Column(Numeric(precision=12, scale=4), nullable=True)
    
    # Enhanced cost basis from processed_premium
    clearing_cost_basis = Column(Numeric(precision=12, scale=2), nullable=True)
    clearing_direction = Column(String(6), nullable=True)  # credit/debit
    
    # Financial metrics
    market_value = Column(Numeric(precision=12, scale=2), nullable=True)
    total_cost = Column(Numeric(precision=12, scale=2), nullable=True)
    total_return = Column(Numeric(precision=12, scale=2), nullable=True)
    total_return_percent = Column(Numeric(precision=8, scale=4), nullable=True)
    
    # Greeks (if available)
    delta = Column(Numeric(precision=8, scale=6), nullable=True)
    gamma = Column(Numeric(precision=8, scale=6), nullable=True)
    theta = Column(Numeric(precision=8, scale=6), nullable=True)
    vega = Column(Numeric(precision=8, scale=6), nullable=True)
    rho = Column(Numeric(precision=8, scale=6), nullable=True)
    
    # Time and volatility
    days_to_expiry = Column(Integer, nullable=True)
    implied_volatility = Column(Numeric(precision=8, scale=4), nullable=True)
    
    # Risk metrics
    break_even_price = Column(Numeric(precision=12, scale=4), nullable=True)
    max_profit = Column(Numeric(precision=12, scale=2), nullable=True)
    max_loss = Column(Numeric(precision=12, scale=2), nullable=True)
    probability_of_profit = Column(Numeric(precision=5, scale=2), nullable=True)
    
    # Raw data from Robinhood
    raw_data = Column(JSONB, nullable=True)
    
    # Timestamps
    opened_at = Column(DateTime(timezone=True), nullable=True)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    user = relationship("User")


# Add indexes for efficient queries
from sqlalchemy import Index
Index("idx_options_positions_user_symbol", OptionsPosition.user_id, OptionsPosition.underlying_symbol)
Index("idx_options_positions_expiry", OptionsPosition.expiration_date)
Index("idx_options_positions_strategy", OptionsPosition.strategy)
Index("idx_options_positions_user_updated", OptionsPosition.user_id, OptionsPosition.last_updated.desc())