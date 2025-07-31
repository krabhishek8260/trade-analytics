"""
Rolled Options Chain Models

Database models for storing pre-computed rolled options chains data
for fast API responses and background processing tracking.
"""

from sqlalchemy import Column, String, DateTime, Numeric, Integer, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import CheckConstraint, Index
import uuid

from app.core.database import Base


class RolledOptionsChain(Base):
    """
    Pre-computed rolled options chain data for fast API responses
    
    Each record represents a complete rolled options chain with all
    orders, financial metrics, and analysis results.
    """
    __tablename__ = "rolled_options_chains"
    
    # Primary identification
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Chain identification (from first order)
    chain_id = Column(String(100), nullable=False, index=True)
    underlying_symbol = Column(String(10), nullable=False, index=True)
    
    # Chain status and metadata
    status = Column(
        String(20), 
        nullable=False, 
        default='active',
        index=True
    )  # 'active', 'closed', 'expired'
    
    initial_strategy = Column(String(50), nullable=True)  # 'short_call', 'long_put', etc.
    start_date = Column(DateTime(timezone=True), nullable=True, index=True)
    last_activity_date = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Order tracking metrics
    total_orders = Column(Integer, nullable=False, default=0)
    roll_count = Column(Integer, nullable=False, default=0)  # total_orders - 1
    
    # Financial metrics (stored as computed values for fast access)
    total_credits_collected = Column(Numeric(12, 2), default=0.0)
    total_debits_paid = Column(Numeric(12, 2), default=0.0)
    net_premium = Column(Numeric(12, 2), default=0.0)
    total_pnl = Column(Numeric(12, 2), default=0.0)  # Realized + Unrealized P&L
    
    # Complete chain data stored as JSON for detailed views
    chain_data = Column(JSONB, nullable=False, default=dict)
    
    # Summary metrics for quick dashboard views
    summary_metrics = Column(JSONB, nullable=False, default=dict)
    
    # Processing metadata
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    user = relationship("User")
    
    # Constraints
    __table_args__ = (
        # Ensure unique chain per user
        CheckConstraint('char_length(chain_id) > 0', name='chain_id_not_empty'),
        CheckConstraint('char_length(underlying_symbol) > 0', name='symbol_not_empty'),
        CheckConstraint('total_orders >= 0', name='total_orders_non_negative'),
        CheckConstraint('roll_count >= 0', name='roll_count_non_negative'),
        CheckConstraint("status IN ('active', 'closed', 'expired')", name='valid_status'),
        
        # Unique constraint for user + chain_id combination
        Index('idx_unique_user_chain', 'user_id', 'chain_id', unique=True),
        
        # Performance indexes
        Index('idx_rolled_chains_user_symbol', 'user_id', 'underlying_symbol'),
        Index('idx_rolled_chains_user_status', 'user_id', 'status'),
        Index('idx_rolled_chains_activity', 'user_id', 'last_activity_date'),
        Index('idx_rolled_chains_chain_lookup', 'chain_id'),
    )
    
    def __repr__(self):
        return f"<RolledOptionsChain(id={self.id}, user_id={self.user_id}, chain_id={self.chain_id}, symbol={self.underlying_symbol}, status={self.status})>"


class UserRolledOptionsSync(Base):
    """
    Tracks the processing status and sync metadata for rolled options 
    background processing for each user.
    """
    __tablename__ = "user_rolled_options_sync"
    
    # Primary key is user_id (one record per user)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )
    
    # Processing timestamps
    last_processed_at = Column(DateTime(timezone=True), nullable=True)
    last_successful_sync = Column(DateTime(timezone=True), nullable=True)
    next_sync_after = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Processing statistics
    total_chains = Column(Integer, default=0)
    active_chains = Column(Integer, default=0)
    closed_chains = Column(Integer, default=0)
    total_orders_processed = Column(Integer, default=0)
    
    # Processing status tracking
    processing_status = Column(
        String(20), 
        default='pending',
        nullable=False,
        index=True
    )  # 'pending', 'processing', 'completed', 'error'
    
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Processing configuration
    full_sync_required = Column(Boolean, default=True)
    incremental_sync_enabled = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('total_chains >= 0', name='total_chains_non_negative'),
        CheckConstraint('active_chains >= 0', name='active_chains_non_negative'),
        CheckConstraint('closed_chains >= 0', name='closed_chains_non_negative'),
        CheckConstraint('total_orders_processed >= 0', name='orders_processed_non_negative'),
        CheckConstraint('retry_count >= 0', name='retry_count_non_negative'),
        CheckConstraint(
            "processing_status IN ('pending', 'processing', 'completed', 'error')", 
            name='valid_processing_status'
        ),
        
        # Performance indexes
        Index('idx_sync_status', 'processing_status'),
        Index('idx_sync_next_sync', 'next_sync_after'),
        Index('idx_sync_error_retry', 'processing_status', 'retry_count'),
    )
    
    def __repr__(self):
        return f"<UserRolledOptionsSync(user_id={self.user_id}, status={self.processing_status}, last_sync={self.last_successful_sync})>"
    
    @property
    def needs_processing(self) -> bool:
        """Check if this user needs rolled options processing"""
        from datetime import datetime
        
        # Never processed
        if self.processing_status == 'pending':
            return True
        
        # Failed and needs retry
        if self.processing_status == 'error' and self.retry_count < 3:
            return True
        
        # Due for scheduled sync
        if (self.next_sync_after and 
            self.next_sync_after <= datetime.now(self.next_sync_after.tzinfo)):
            return True
        
        return False
    
    @property
    def is_processing(self) -> bool:
        """Check if processing is currently in progress"""
        return self.processing_status == 'processing'
    
    @property
    def processing_summary(self) -> dict:
        """Get a summary of processing status for API responses"""
        return {
            'status': self.processing_status,
            'last_processed': self.last_processed_at.isoformat() if self.last_processed_at else None,
            'last_successful': self.last_successful_sync.isoformat() if self.last_successful_sync else None,
            'next_sync': self.next_sync_after.isoformat() if self.next_sync_after else None,
            'total_chains': self.total_chains,
            'active_chains': self.active_chains,
            'closed_chains': self.closed_chains,
            'orders_processed': self.total_orders_processed,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'needs_processing': self.needs_processing
        }


# Create additional indexes after table definition
def create_additional_indexes():
    """
    Create additional indexes that couldn't be defined in __table_args__
    These are run as part of migrations.
    """
    additional_indexes = [
        # Composite indexes for common query patterns
        Index(
            'idx_rolled_chains_user_symbol_status', 
            RolledOptionsChain.user_id, 
            RolledOptionsChain.underlying_symbol, 
            RolledOptionsChain.status
        ),
        Index(
            'idx_rolled_chains_user_activity_desc', 
            RolledOptionsChain.user_id, 
            RolledOptionsChain.last_activity_date.desc()
        ),
        Index(
            'idx_rolled_chains_pnl', 
            RolledOptionsChain.user_id, 
            RolledOptionsChain.total_pnl.desc()
        ),
        
        # Sync status indexes
        Index(
            'idx_sync_pending_users', 
            UserRolledOptionsSync.processing_status, 
            UserRolledOptionsSync.next_sync_after
        ),
    ]
    
    return additional_indexes