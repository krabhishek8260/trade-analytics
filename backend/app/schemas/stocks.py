"""
Stocks schemas
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime


class StockPositionBase(BaseModel):
    """Base stock position schema"""
    symbol: str = Field(..., max_length=10)
    quantity: Decimal = Field(...)
    average_buy_price: Decimal = Field(...)


class StockPositionCreate(StockPositionBase):
    """Stock position creation schema"""
    current_price: Optional[Decimal] = Field(default=None)
    raw_data: Optional[Dict[str, Any]] = Field(default=None)


class StockPositionUpdate(BaseModel):
    """Stock position update schema"""
    current_price: Optional[Decimal] = Field(default=None)
    market_value: Optional[Decimal] = Field(default=None)
    total_return: Optional[Decimal] = Field(default=None)
    total_return_percent: Optional[Decimal] = Field(default=None)


class StockPositionResponse(StockPositionBase):
    """Stock position response schema"""
    id: str = Field(...)
    user_id: str = Field(...)
    
    # Current pricing
    current_price: Optional[Decimal] = Field(default=None)
    
    # Financial metrics
    market_value: Optional[Decimal] = Field(default=None)
    total_cost: Optional[Decimal] = Field(default=None)
    total_return: Optional[Decimal] = Field(default=None)
    total_return_percent: Optional[Decimal] = Field(default=None)
    
    # Timestamps
    last_updated: datetime = Field(...)
    created_at: datetime = Field(...)
    
    class Config:
        from_attributes = True


class StocksSummary(BaseModel):
    """Stocks portfolio summary"""
    total_positions: int = Field(...)
    total_value: Decimal = Field(...)
    total_cost: Decimal = Field(...)
    total_return: Decimal = Field(...)
    total_return_percent: Decimal = Field(...)
    
    # Performance metrics
    winners: int = Field(default=0)
    losers: int = Field(default=0)
    win_rate: Optional[Decimal] = Field(default=None)
    
    # Sector breakdown
    sector_allocation: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    # Top performers
    top_gainers: list[Dict[str, Any]] = Field(default_factory=list)
    top_losers: list[Dict[str, Any]] = Field(default_factory=list)
    
    last_updated: datetime = Field(...)


class StockQuote(BaseModel):
    """Stock quote data"""
    symbol: str = Field(...)
    price: Decimal = Field(...)
    change: Optional[Decimal] = Field(default=None)
    change_percent: Optional[Decimal] = Field(default=None)
    volume: Optional[int] = Field(default=None)
    market_cap: Optional[Decimal] = Field(default=None)
    pe_ratio: Optional[Decimal] = Field(default=None)
    timestamp: datetime = Field(...)


class StockOrder(BaseModel):
    """Stock order data"""
    order_id: str = Field(...)
    symbol: str = Field(...)
    side: str = Field(...)  # buy/sell
    quantity: Decimal = Field(...)
    price: Optional[Decimal] = Field(default=None)
    type: str = Field(default="market")  # market/limit
    state: str = Field(...)
    created_at: datetime = Field(...)
    updated_at: Optional[datetime] = Field(default=None)