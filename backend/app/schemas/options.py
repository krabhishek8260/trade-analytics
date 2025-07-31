"""
Options schemas with enhanced trading analysis
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime, date
from enum import Enum


class OptionType(str, Enum):
    """Option type enum"""
    CALL = "call"
    PUT = "put"


class TransactionSide(str, Enum):
    """Transaction side enum"""
    BUY = "buy"
    SELL = "sell"


class PositionEffect(str, Enum):
    """Position effect enum"""
    OPEN = "open"
    CLOSE = "close"


class Direction(str, Enum):
    """Direction enum"""
    CREDIT = "credit"
    DEBIT = "debit"


class OptionsPositionBase(BaseModel):
    """Base options position schema"""
    underlying_symbol: str = Field(..., max_length=10)
    option_type: OptionType = Field(...)
    strike_price: Decimal = Field(...)
    expiration_date: date = Field(...)
    quantity: Decimal = Field(...)
    contracts: int = Field(...)
    transaction_side: TransactionSide = Field(...)
    position_effect: PositionEffect = Field(...)
    direction: Direction = Field(...)
    strategy: Optional[str] = Field(default=None)
    strategy_type: Optional[str] = Field(default=None)


class OptionsPositionCreate(OptionsPositionBase):
    """Options position creation schema"""
    average_price: Optional[Decimal] = Field(default=None)
    current_price: Optional[Decimal] = Field(default=None)
    clearing_cost_basis: Optional[Decimal] = Field(default=None)
    clearing_direction: Optional[Direction] = Field(default=None)
    raw_data: Optional[Dict[str, Any]] = Field(default=None)


class OptionsPositionUpdate(BaseModel):
    """Options position update schema"""
    current_price: Optional[Decimal] = Field(default=None)
    market_value: Optional[Decimal] = Field(default=None)
    total_return: Optional[Decimal] = Field(default=None)
    total_return_percent: Optional[Decimal] = Field(default=None)
    delta: Optional[Decimal] = Field(default=None)
    gamma: Optional[Decimal] = Field(default=None)
    theta: Optional[Decimal] = Field(default=None)
    vega: Optional[Decimal] = Field(default=None)
    rho: Optional[Decimal] = Field(default=None)
    implied_volatility: Optional[Decimal] = Field(default=None)


class OptionsPositionResponse(OptionsPositionBase):
    """Options position response schema"""
    id: str = Field(...)
    user_id: str = Field(...)
    
    # Pricing
    average_price: Optional[Decimal] = Field(default=None)
    current_price: Optional[Decimal] = Field(default=None)
    clearing_cost_basis: Optional[Decimal] = Field(default=None)
    clearing_direction: Optional[Direction] = Field(default=None)
    
    # Financial metrics
    market_value: Optional[Decimal] = Field(default=None)
    total_cost: Optional[Decimal] = Field(default=None)
    total_return: Optional[Decimal] = Field(default=None)
    total_return_percent: Optional[Decimal] = Field(default=None)
    
    # Greeks
    delta: Optional[Decimal] = Field(default=None)
    gamma: Optional[Decimal] = Field(default=None)
    theta: Optional[Decimal] = Field(default=None)
    vega: Optional[Decimal] = Field(default=None)
    rho: Optional[Decimal] = Field(default=None)
    
    # Time and volatility
    days_to_expiry: Optional[int] = Field(default=None)
    implied_volatility: Optional[Decimal] = Field(default=None)
    
    # Risk metrics
    break_even_price: Optional[Decimal] = Field(default=None)
    max_profit: Optional[Decimal] = Field(default=None)
    max_loss: Optional[Decimal] = Field(default=None)
    probability_of_profit: Optional[Decimal] = Field(default=None)
    
    # Timestamps
    opened_at: Optional[datetime] = Field(default=None)
    last_updated: datetime = Field(...)
    created_at: datetime = Field(...)
    
    class Config:
        from_attributes = True


class OptionsLeg(BaseModel):
    """Options leg for multi-leg strategies"""
    leg_index: int = Field(...)
    side: TransactionSide = Field(...)
    position_effect: PositionEffect = Field(...)
    option_type: OptionType = Field(...)
    quantity: Decimal = Field(...)
    ratio_quantity: Decimal = Field(...)
    underlying_symbol: str = Field(...)
    strike_price: Decimal = Field(...)
    expiration_date: str = Field(...)
    instrument_id: str = Field(...)


class OptionsExecution(BaseModel):
    """Options execution details"""
    execution_id: str = Field(...)
    price: Decimal = Field(...)
    quantity: Decimal = Field(...)
    settlement_date: str = Field(...)
    timestamp: datetime = Field(...)


class OptionsOrderBase(BaseModel):
    """Base options order schema"""
    underlying_symbol: str = Field(..., max_length=10)
    strategy: Optional[str] = Field(default=None)
    direction: Direction = Field(...)
    state: str = Field(...)
    type: str = Field(default="limit")
    quantity: Decimal = Field(...)


class OptionsOrderCreate(OptionsOrderBase):
    """Options order creation schema"""
    order_id: str = Field(...)
    price: Optional[Decimal] = Field(default=None)
    premium: Optional[Decimal] = Field(default=None)
    processed_premium: Optional[Decimal] = Field(default=None)
    processed_premium_direction: Optional[Direction] = Field(default=None)
    legs: Optional[List[OptionsLeg]] = Field(default=None)
    executions: Optional[List[OptionsExecution]] = Field(default=None)
    raw_data: Optional[Dict[str, Any]] = Field(default=None)


class OptionsOrderResponse(OptionsOrderBase):
    """Options order response schema"""
    id: str = Field(...)
    user_id: str = Field(...)
    order_id: str = Field(...)
    
    # Pricing
    price: Optional[Decimal] = Field(default=None)
    premium: Optional[Decimal] = Field(default=None)
    processed_premium: Optional[Decimal] = Field(default=None)
    processed_premium_direction: Optional[Direction] = Field(default=None)
    
    # Multi-leg information
    legs_count: int = Field(default=1)
    legs: Optional[List[OptionsLeg]] = Field(default=None)
    executions_count: int = Field(default=0)
    executions: Optional[List[OptionsExecution]] = Field(default=None)
    
    # Single leg info (for compatibility)
    option_type: Optional[OptionType] = Field(default=None)
    strike_price: Optional[Decimal] = Field(default=None)
    expiration_date: Optional[str] = Field(default=None)
    transaction_side: Optional[TransactionSide] = Field(default=None)
    position_effect: Optional[PositionEffect] = Field(default=None)
    
    # Financial summary
    total_cost: Optional[Decimal] = Field(default=None)
    fees: Optional[Decimal] = Field(default=None)
    net_amount: Optional[Decimal] = Field(default=None)
    
    # Timestamps
    order_created_at: Optional[datetime] = Field(default=None)
    order_updated_at: Optional[datetime] = Field(default=None)
    filled_at: Optional[datetime] = Field(default=None)
    cancelled_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(...)
    
    class Config:
        from_attributes = True


class OptionsStrategy(BaseModel):
    """Options strategy analysis"""
    name: str = Field(...)
    type: str = Field(...)  # single_leg, spread, combination
    legs: List[OptionsLeg] = Field(...)
    
    # Risk/Reward
    max_profit: Optional[Decimal] = Field(default=None)
    max_loss: Optional[Decimal] = Field(default=None)
    break_even_points: List[Decimal] = Field(default_factory=list)
    
    # Greeks
    net_delta: Optional[Decimal] = Field(default=None)
    net_gamma: Optional[Decimal] = Field(default=None)
    net_theta: Optional[Decimal] = Field(default=None)
    net_vega: Optional[Decimal] = Field(default=None)
    
    # Analysis
    probability_of_profit: Optional[Decimal] = Field(default=None)
    risk_reward_ratio: Optional[Decimal] = Field(default=None)
    recommended_action: Optional[str] = Field(default=None)


class OptionsSummary(BaseModel):
    """Options portfolio summary"""
    total_positions: int = Field(...)
    total_value: Decimal = Field(...)
    total_return: Decimal = Field(...)
    total_return_percent: Decimal = Field(...)
    
    # Breakdown by strategy
    long_positions: int = Field(default=0)
    short_positions: int = Field(default=0)
    calls_count: int = Field(default=0)
    puts_count: int = Field(default=0)
    
    # Risk metrics
    total_delta: Optional[Decimal] = Field(default=None)
    total_gamma: Optional[Decimal] = Field(default=None)
    total_theta: Optional[Decimal] = Field(default=None)
    total_vega: Optional[Decimal] = Field(default=None)
    
    # Expiry analysis
    expiring_this_week: int = Field(default=0)
    expiring_this_month: int = Field(default=0)
    
    # Performance
    winners: int = Field(default=0)
    losers: int = Field(default=0)
    win_rate: Optional[Decimal] = Field(default=None)
    
    last_updated: datetime = Field(...)