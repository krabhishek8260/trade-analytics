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
    """Options position model aligned with API data structures"""
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
    
    # Core Position Fields (aligned with API)
    chain_symbol = Column(String(20), nullable=False, index=True)  # Use chain_symbol like orders
    option_type = Column(String(4), nullable=False)  # call/put
    strike_price = Column(Numeric(precision=12, scale=4), nullable=False, index=True)
    expiration_date = Column(Date, nullable=False, index=True)
    
    # Position Details
    quantity = Column(Numeric(precision=12, scale=4), nullable=False)  # Signed quantity
    contracts = Column(Integer, nullable=False)  # Absolute number of contracts
    position_type = Column(String(5), nullable=False)  # long/short
    
    # Transaction Details
    transaction_side = Column(String(4), nullable=False)  # buy/sell
    position_effect = Column(String(5), nullable=False)   # open/close
    direction = Column(String(6), nullable=False)         # credit/debit
    
    # Strategy Classification
    strategy = Column(String(50), nullable=True)  # BUY CALL, SELL PUT, etc.
    
    # Pricing Information
    average_price = Column(Numeric(precision=12, scale=4), nullable=True)  # Average price per share
    current_price = Column(Numeric(precision=12, scale=4), nullable=True)  # Current market price per share
    
    # Enhanced Cost Basis (from processed_premium)
    clearing_cost_basis = Column(Numeric(precision=12, scale=2), nullable=True)  # Total cost basis
    clearing_direction = Column(String(6), nullable=True)  # credit/debit
    
    # Financial Metrics
    market_value = Column(Numeric(precision=12, scale=2), nullable=True)  # Current market value
    total_cost = Column(Numeric(precision=12, scale=2), nullable=True)    # Total cost paid
    total_return = Column(Numeric(precision=12, scale=2), nullable=True)  # Unrealized P&L
    percent_change = Column(Numeric(precision=8, scale=4), nullable=True)  # % return
    
    # Greeks (market data)
    delta = Column(Numeric(precision=8, scale=6), nullable=True)
    gamma = Column(Numeric(precision=8, scale=6), nullable=True)
    theta = Column(Numeric(precision=8, scale=6), nullable=True)
    vega = Column(Numeric(precision=8, scale=6), nullable=True)
    rho = Column(Numeric(precision=8, scale=6), nullable=True)
    implied_volatility = Column(Numeric(precision=8, scale=4), nullable=True)
    open_interest = Column(Integer, nullable=True)
    
    # Time Metrics
    days_to_expiry = Column(Integer, nullable=True)
    
    # System Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Raw data from Robinhood (for debugging/backup)
    raw_data = Column(JSONB, nullable=True)
    
    # Relationships
    user = relationship("User")


# Add indexes for efficient queries
from sqlalchemy import Index

# Core query patterns
Index("idx_options_positions_user_symbol", OptionsPosition.user_id, OptionsPosition.chain_symbol)
Index("idx_options_positions_user_expiry", OptionsPosition.user_id, OptionsPosition.expiration_date)
Index("idx_options_positions_user_updated", OptionsPosition.user_id, OptionsPosition.updated_at.desc())

# Position analysis queries
Index("idx_options_positions_strategy", OptionsPosition.strategy)
Index("idx_options_positions_type_strike", OptionsPosition.option_type, OptionsPosition.strike_price)
Index("idx_options_positions_expiry_range", OptionsPosition.expiration_date)