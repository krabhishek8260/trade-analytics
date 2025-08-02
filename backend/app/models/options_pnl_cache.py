"""
Options P&L Cache Models

Database models for storing pre-computed P&L analytics to avoid
recalculating complex realized P&L on every request.
"""

from sqlalchemy import Column, String, DateTime, Numeric, Integer, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import CheckConstraint, Index
import uuid

from app.core.database import Base


class UserOptionsPnLCache(Base):
    """
    Cached P&L analytics per user
    
    Stores comprehensive P&L data that's expensive to calculate,
    updated by background tasks.
    """
    __tablename__ = "user_options_pnl_cache"
    
    # Primary key is user_id (one record per user)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )
    
    # Overall P&L Metrics
    total_pnl = Column(Numeric(12, 2), default=0.0)
    realized_pnl = Column(Numeric(12, 2), default=0.0)
    unrealized_pnl = Column(Numeric(12, 2), default=0.0)
    
    # Trade Statistics
    total_trades = Column(Integer, default=0)
    realized_trades = Column(Integer, default=0)
    open_positions = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Numeric(5, 2), default=0.0)
    
    # Performance Metrics
    largest_winner = Column(Numeric(12, 2), default=0.0)
    largest_loser = Column(Numeric(12, 2), default=0.0)
    avg_trade_pnl = Column(Numeric(12, 2), default=0.0)
    
    # Detailed Breakdowns (stored as JSON for flexibility)
    yearly_breakdown = Column(JSONB, nullable=False, default=list)
    symbol_breakdown = Column(JSONB, nullable=False, default=list)
    monthly_breakdown = Column(JSONB, nullable=False, default=list)
    
    # Processing metadata
    last_calculated_at = Column(DateTime(timezone=True), nullable=True)
    calculation_status = Column(
        String(20), 
        default='pending',
        nullable=False,
        index=True
    )  # 'pending', 'processing', 'completed', 'error'
    
    error_message = Column(Text, nullable=True)
    orders_processed = Column(Integer, default=0)
    positions_processed = Column(Integer, default=0)
    
    # Data freshness tracking
    last_order_date = Column(DateTime(timezone=True), nullable=True)
    needs_recalculation = Column(Boolean, default=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('total_trades >= 0', name='total_trades_non_negative'),
        CheckConstraint('realized_trades >= 0', name='realized_trades_non_negative'),
        CheckConstraint('open_positions >= 0', name='open_positions_non_negative'),
        CheckConstraint('winning_trades >= 0', name='winning_trades_non_negative'),
        CheckConstraint('losing_trades >= 0', name='losing_trades_non_negative'),
        CheckConstraint('orders_processed >= 0', name='orders_processed_non_negative'),
        CheckConstraint('positions_processed >= 0', name='positions_processed_non_negative'),
        CheckConstraint(
            "calculation_status IN ('pending', 'processing', 'completed', 'error')", 
            name='valid_calculation_status'
        ),
        
        # Performance indexes
        Index('idx_pnl_cache_status', 'calculation_status'),
        Index('idx_pnl_cache_needs_recalc', 'needs_recalculation'),
        Index('idx_pnl_cache_last_calc', 'last_calculated_at'),
    )
    
    def __repr__(self):
        return f"<UserOptionsPnLCache(user_id={self.user_id}, status={self.calculation_status}, total_pnl={self.total_pnl})>"
    
    @property
    def is_stale(self) -> bool:
        """Check if the cached data is stale and needs recalculation"""
        return (
            self.needs_recalculation or 
            self.calculation_status in ('pending', 'error') or
            self.last_calculated_at is None
        )
    
    @property
    def calculation_summary(self) -> dict:
        """Get a summary of the calculation state for API responses"""
        return {
            'status': self.calculation_status,
            'last_calculated': self.last_calculated_at.isoformat() if self.last_calculated_at else None,
            'orders_processed': self.orders_processed,
            'positions_processed': self.positions_processed,
            'needs_recalculation': self.needs_recalculation,
            'is_stale': self.is_stale,
            'error_message': self.error_message
        }
    
    def to_analytics_dict(self) -> dict:
        """Convert to the format expected by the frontend"""
        return {
            'total_pnl': float(self.total_pnl or 0),
            'realized_pnl': float(self.realized_pnl or 0),
            'unrealized_pnl': float(self.unrealized_pnl or 0),
            'total_trades': self.total_trades or 0,
            'realized_trades': self.realized_trades or 0,
            'open_positions': self.open_positions or 0,
            'winning_trades': self.winning_trades or 0,
            'losing_trades': self.losing_trades or 0,
            'win_rate': float(self.win_rate or 0),
            'largest_winner': float(self.largest_winner or 0),
            'largest_loser': float(self.largest_loser or 0),
            'avg_trade_pnl': float(self.avg_trade_pnl or 0)
        }


class OptionsPnLProcessingLog(Base):
    """
    Log of P&L processing runs for debugging and monitoring
    """
    __tablename__ = "options_pnl_processing_log"
    
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
    
    # Processing details
    processing_type = Column(String(50), nullable=False)  # 'full', 'incremental', 'repair'
    status = Column(String(20), nullable=False)  # 'started', 'completed', 'error'
    
    # Statistics
    orders_found = Column(Integer, default=0)
    orders_processed = Column(Integer, default=0)
    trades_matched = Column(Integer, default=0)
    positions_processed = Column(Integer, default=0)
    
    # Performance metrics
    processing_time_seconds = Column(Numeric(8, 3), nullable=True)
    memory_usage_mb = Column(Numeric(8, 2), nullable=True)
    
    # Results
    total_pnl_calculated = Column(Numeric(12, 2), nullable=True)
    error_message = Column(Text, nullable=True)
    error_details = Column(JSONB, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('orders_found >= 0', name='orders_found_non_negative'),
        CheckConstraint('orders_processed >= 0', name='orders_processed_non_negative'),
        CheckConstraint('trades_matched >= 0', name='trades_matched_non_negative'),
        CheckConstraint('positions_processed >= 0', name='positions_processed_non_negative'),
        CheckConstraint(
            "processing_type IN ('full', 'incremental', 'repair')", 
            name='valid_processing_type'
        ),
        CheckConstraint(
            "status IN ('started', 'completed', 'error')", 
            name='valid_processing_status'
        ),
        
        # Performance indexes
        Index('idx_pnl_log_user_date', 'user_id', 'started_at'),
        Index('idx_pnl_log_status', 'status'),
        Index('idx_pnl_log_type', 'processing_type'),
    )
    
    def __repr__(self):
        return f"<OptionsPnLProcessingLog(user_id={self.user_id}, type={self.processing_type}, status={self.status})>"


# Create additional indexes after table definition
def create_additional_pnl_indexes():
    """
    Create additional indexes that couldn't be defined in __table_args__
    These should be run as part of migrations.
    """
    additional_indexes = [
        # Composite indexes for common query patterns
        Index(
            'idx_pnl_cache_user_status_calc', 
            UserOptionsPnLCache.user_id, 
            UserOptionsPnLCache.calculation_status,
            UserOptionsPnLCache.last_calculated_at
        ),
        Index(
            'idx_pnl_log_user_recent', 
            OptionsPnLProcessingLog.user_id, 
            OptionsPnLProcessingLog.started_at.desc()
        ),
    ]
    
    return additional_indexes