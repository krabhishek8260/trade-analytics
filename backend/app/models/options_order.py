"""
Options order model aligned with Robinhood API data structures
"""

from sqlalchemy import Column, String, DateTime, Numeric, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class OptionsOrder(Base):
    """Options order model with API-aligned fields and top-level leg data"""
    __tablename__ = "options_orders"
    
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
    
    # Core Order Fields (from API documentation)
    order_id = Column(String, unique=True, nullable=False, index=True)  # Robinhood order ID
    state = Column(String(20), nullable=False, index=True)  # filled, queued, confirmed, etc.
    type = Column(String(20), nullable=False)  # limit, market
    chain_id = Column(String(100), nullable=True, index=True)  # Options chain identifier
    chain_symbol = Column(String(20), nullable=True, index=True)  # Underlying asset symbol
    
    # Financial Fields (from API documentation)
    processed_quantity = Column(Numeric(precision=12, scale=4), nullable=True)  # Contracts filled
    processed_premium = Column(Numeric(precision=12, scale=2), nullable=True)  # Total premium processed
    premium = Column(Numeric(precision=12, scale=4), nullable=True)  # Premium per contract
    direction = Column(String(6), nullable=True)  # credit or debit
    
    # Strategy Fields (from API documentation)
    strategy = Column(String(50), nullable=True)  # Overall strategy name
    opening_strategy = Column(String(50), nullable=True)  # Strategy when opening
    closing_strategy = Column(String(50), nullable=True)  # Strategy when closing
    
    # Timing Fields (from API documentation)
    created_at = Column(DateTime(timezone=True), nullable=True)  # From API
    updated_at = Column(DateTime(timezone=True), nullable=True)  # From API
    
    # Leg Information (from API documentation)
    legs_count = Column(Integer, nullable=False, default=0)  # Number of legs
    legs_details = Column(JSONB, nullable=True)  # Full legs data as JSONB
    
    # Top-Level Leg Fields (extracted from legs for querying)
    # These represent the primary/first leg for single-leg orders or main leg for multi-leg
    leg_index = Column(Integer, nullable=True)  # Index of this leg (0-based)
    leg_id = Column(String, nullable=True)  # Unique identifier for this specific leg
    side = Column(String(4), nullable=True)  # buy or sell
    position_effect = Column(String(5), nullable=True)  # open or close
    option_type = Column(String(4), nullable=True)  # call or put
    strike_price = Column(Numeric(precision=12, scale=4), nullable=True)  # Strike price
    expiration_date = Column(String(10), nullable=True)  # YYYY-MM-DD format
    long_strategy_code = Column(String(100), nullable=True)  # Long leg tracking code
    short_strategy_code = Column(String(100), nullable=True)  # Short leg tracking code
    
    # System timestamps
    db_created_at = Column(DateTime(timezone=True), server_default=func.now())
    db_updated_at = Column(
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

# Core query patterns for options history
Index("idx_options_orders_user_created", OptionsOrder.user_id, OptionsOrder.created_at.desc())
Index("idx_options_orders_user_updated", OptionsOrder.user_id, OptionsOrder.updated_at.desc())
Index("idx_options_orders_user_chain", OptionsOrder.user_id, OptionsOrder.chain_symbol)
Index("idx_options_orders_user_state", OptionsOrder.user_id, OptionsOrder.state)

# Strategy and chain tracking
Index("idx_options_orders_chain_id", OptionsOrder.chain_id)
Index("idx_options_orders_strategy", OptionsOrder.strategy)
Index("idx_options_orders_user_strategy", OptionsOrder.user_id, OptionsOrder.strategy)

# Leg-based queries
Index("idx_options_orders_user_strike_expiry", OptionsOrder.user_id, OptionsOrder.strike_price, OptionsOrder.expiration_date)
Index("idx_options_orders_user_option_type", OptionsOrder.user_id, OptionsOrder.option_type)
Index("idx_options_orders_position_effect", OptionsOrder.position_effect)

# Pagination and sorting optimizations for history view
Index("idx_options_orders_user_created_id", OptionsOrder.user_id, OptionsOrder.created_at.desc(), OptionsOrder.id)
Index("idx_options_orders_user_symbol_created", OptionsOrder.user_id, OptionsOrder.chain_symbol, OptionsOrder.created_at.desc())
Index("idx_options_orders_user_state_created", OptionsOrder.user_id, OptionsOrder.state, OptionsOrder.created_at.desc())

# JSONB index for legs_details queries (GIN index for JSON operations)
Index("idx_options_orders_legs_details_gin", OptionsOrder.legs_details, postgresql_using='gin')