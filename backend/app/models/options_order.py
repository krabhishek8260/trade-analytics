"""
Options order model with legs and executions
"""

from sqlalchemy import Column, String, DateTime, Numeric, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class OptionsOrder(Base):
    """Options order model with full legs and executions data"""
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
    
    # Order identification
    order_id = Column(String, unique=True, nullable=False, index=True)  # Robinhood order ID
    
    # Chain tracking for rolled options
    chain_id = Column(String(100), nullable=True, index=True)  # Robinhood chain ID
    chain_symbol = Column(String(20), nullable=True, index=True)  # Chain symbol
    closing_strategy = Column(String(50), nullable=True)  # Strategy when closing
    opening_strategy = Column(String(50), nullable=True)  # Strategy when opening
    
    # Basic order info
    underlying_symbol = Column(String(10), nullable=False, index=True)
    strategy = Column(String(50), nullable=True)  # Strategy name if multi-leg
    direction = Column(String(6), nullable=False)  # credit/debit
    state = Column(String(20), nullable=False)     # filled/cancelled/pending
    type = Column(String(20), nullable=False)      # limit/market
    
    # Order quantities and pricing
    quantity = Column(Numeric(precision=12, scale=4), nullable=False)
    price = Column(Numeric(precision=12, scale=4), nullable=True)
    premium = Column(Numeric(precision=12, scale=2), nullable=True)
    
    # Enhanced pricing from processed_premium (accurate cost basis)
    processed_premium = Column(Numeric(precision=12, scale=2), nullable=True)
    processed_premium_direction = Column(String(6), nullable=True)  # credit/debit
    
    # Multi-leg information
    legs_count = Column(Integer, nullable=False, default=1)
    legs = Column(JSONB, nullable=True)  # Detailed legs data
    
    # Execution details
    executions = Column(JSONB, nullable=True)  # All executions
    executions_count = Column(Integer, nullable=False, default=0)
    
    # Single leg info (for compatibility and simple queries)
    option_type = Column(String(4), nullable=True)      # call/put
    strike_price = Column(Numeric(precision=12, scale=4), nullable=True)
    expiration_date = Column(String, nullable=True)     # ISO date string
    transaction_side = Column(String(4), nullable=True)  # buy/sell
    position_effect = Column(String(5), nullable=True)   # open/close
    
    # Financial summary
    total_cost = Column(Numeric(precision=12, scale=2), nullable=True)
    fees = Column(Numeric(precision=8, scale=2), nullable=True)
    net_amount = Column(Numeric(precision=12, scale=2), nullable=True)
    
    # Raw data from Robinhood
    raw_data = Column(JSONB, nullable=True)
    
    # Timestamps
    order_created_at = Column(DateTime(timezone=True), nullable=True)  # From Robinhood
    order_updated_at = Column(DateTime(timezone=True), nullable=True)  # From Robinhood
    filled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    
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
Index("idx_options_orders_user_created", OptionsOrder.user_id, OptionsOrder.order_created_at.desc())
Index("idx_options_orders_user_symbol", OptionsOrder.user_id, OptionsOrder.underlying_symbol)
Index("idx_options_orders_state", OptionsOrder.state)
Index("idx_options_orders_strategy", OptionsOrder.strategy)
Index("idx_options_orders_chain_id", OptionsOrder.chain_id)
Index("idx_options_orders_chain_symbol", OptionsOrder.chain_symbol)
Index("idx_options_orders_user_chain", OptionsOrder.user_id, OptionsOrder.chain_id)