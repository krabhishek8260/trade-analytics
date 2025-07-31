"""
Job Execution Log Model

Tracks the execution history of background jobs for monitoring and analytics.
"""

from sqlalchemy import Column, String, DateTime, Integer, Float, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
import uuid
from datetime import datetime


class JobExecutionLog(Base):
    """Log entries for background job executions"""
    __tablename__ = "job_execution_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Job identification
    job_name = Column(String(100), nullable=False, index=True)
    job_id = Column(String(100), nullable=False)
    
    # Execution timing
    started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Execution results
    status = Column(String(20), nullable=False, index=True)  # 'success', 'error', 'timeout'
    error_message = Column(Text, nullable=True)
    
    # Processing metrics (for rolled options jobs)
    users_processed = Column(Integer, default=0)
    chains_processed = Column(Integer, default=0)
    orders_processed = Column(Integer, default=0)
    
    # Resource usage
    memory_usage_mb = Column(Float, nullable=True)
    cpu_time_seconds = Column(Float, nullable=True)
    
    # Metadata
    triggered_manually = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<JobExecutionLog(job_name='{self.job_name}', status='{self.status}', duration={self.duration_seconds}s)>"
    
    @property
    def execution_summary(self) -> dict:
        """Return a summary of the job execution"""
        return {
            "job_name": self.job_name,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "users_processed": self.users_processed,
            "chains_processed": self.chains_processed,
            "orders_processed": self.orders_processed,
            "error_message": self.error_message,
            "triggered_manually": self.triggered_manually
        }