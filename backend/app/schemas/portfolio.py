"""
Portfolio schemas
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime


class PortfolioBase(BaseModel):
    """Base portfolio schema"""
    total_value: Optional[Decimal] = Field(default=None)
    total_return: Optional[Decimal] = Field(default=None)
    total_return_percent: Optional[Decimal] = Field(default=None)
    day_return: Optional[Decimal] = Field(default=None)
    day_return_percent: Optional[Decimal] = Field(default=None)
    stocks_value: Optional[Decimal] = Field(default=None)
    options_value: Optional[Decimal] = Field(default=None)
    cash_value: Optional[Decimal] = Field(default=None)


class PortfolioCreate(PortfolioBase):
    """Portfolio creation schema"""
    raw_data: Optional[Dict[str, Any]] = Field(default=None)


class PortfolioUpdate(PortfolioBase):
    """Portfolio update schema"""
    pass


class PortfolioResponse(PortfolioBase):
    """Portfolio response schema"""
    id: str = Field(...)
    user_id: str = Field(...)
    snapshot_date: datetime = Field(...)
    created_at: datetime = Field(...)
    raw_data: Optional[Dict[str, Any]] = Field(default=None)
    
    class Config:
        from_attributes = True


class PortfolioSummary(BaseModel):
    """Portfolio summary for dashboard"""
    # Current values
    total_value: Decimal = Field(...)
    total_return: Decimal = Field(...)
    total_return_percent: Decimal = Field(...)
    day_return: Decimal = Field(...)
    day_return_percent: Decimal = Field(...)
    
    # Breakdown
    stocks_value: Decimal = Field(...)
    stocks_count: int = Field(...)
    options_value: Decimal = Field(...)
    options_count: int = Field(...)
    cash_value: Decimal = Field(...)
    
    # Performance metrics
    week_return: Optional[Decimal] = Field(default=None)
    month_return: Optional[Decimal] = Field(default=None)
    year_return: Optional[Decimal] = Field(default=None)
    
    # Risk metrics
    max_drawdown: Optional[Decimal] = Field(default=None)
    sharpe_ratio: Optional[Decimal] = Field(default=None)
    volatility: Optional[Decimal] = Field(default=None)
    
    # Last updated
    last_updated: datetime = Field(...)


class PortfolioAllocation(BaseModel):
    """Portfolio allocation breakdown"""
    stocks_percent: Decimal = Field(...)
    options_percent: Decimal = Field(...)
    cash_percent: Decimal = Field(...)
    
    # Sector allocation
    sector_allocation: Dict[str, Decimal] = Field(default_factory=dict)
    
    # Top holdings
    top_holdings: list[Dict[str, Any]] = Field(default_factory=list)


class PortfolioPerformance(BaseModel):
    """Portfolio performance over time"""
    dates: list[str] = Field(default_factory=list)
    values: list[Decimal] = Field(default_factory=list)
    returns: list[Decimal] = Field(default_factory=list)
    
    # Benchmark comparison
    benchmark_values: Optional[list[Decimal]] = Field(default=None)
    benchmark_returns: Optional[list[Decimal]] = Field(default=None)