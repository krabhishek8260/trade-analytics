"""
Schemas for options portfolio breakdown responses

These schemas define the structure for detailed breakdowns of portfolio metrics
that enable interactive drill-down functionality in the frontend.
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel
from enum import Enum

class GroupingType(str, Enum):
    """Types of data grouping available for drill-down"""
    SYMBOL = "symbol"
    STRATEGY = "strategy" 
    EXPIRY = "expiry"
    GREEKS = "greeks"
    POSITION_TYPE = "position_type"

class SortType(str, Enum):
    """Sorting options for breakdown data"""
    VALUE = "value"
    RETURN = "return"
    PERCENTAGE = "percentage"
    ALPHABETICAL = "alphabetical"
    DATE = "date"

class PositionBreakdown(BaseModel):
    """Individual position details within a breakdown component"""
    position_id: str
    underlying_symbol: str
    chain_symbol: Optional[str] = None
    option_type: str
    strike_price: float
    expiration_date: str
    contracts: float
    market_value: float
    total_cost: float
    total_return: float
    percent_change: float
    strategy: str

class BreakdownComponent(BaseModel):
    """A component within a portfolio breakdown"""
    id: str
    name: str
    display_name: str
    value: float
    percentage: float
    position_count: int
    component_type: str  # "long", "short", "spread", "strategy", etc.
    underlying_symbol: Optional[str] = None
    strategy: Optional[str] = None
    positions: List[PositionBreakdown] = []
    
    # Aggregate metrics for this component
    total_return: float
    return_percentage: float
    market_value: float
    cost_basis: float

class CalculationStep(BaseModel):
    """A step in the calculation process"""
    step_number: int
    description: str
    formula: str
    values: Dict[str, Union[float, str]]
    result: float

class CalculationDetails(BaseModel):
    """Detailed explanation of how a metric is calculated"""
    metric_name: str
    final_formula: str
    explanation: str
    example: str
    calculation_steps: List[CalculationStep]
    components_used: List[str]
    methodology_notes: List[str]

class DrillDownLevel(BaseModel):
    """A level in the drill-down hierarchy"""
    level: int
    name: str
    description: str
    grouping: GroupingType
    total_groups: int
    data: List[BreakdownComponent]

class BreakdownResponse(BaseModel):
    """Complete breakdown response for a portfolio metric"""
    metric_name: str
    metric_display_name: str
    total_value: float
    calculation_method: str
    last_updated: str
    
    # Main breakdown data
    summary: Dict[str, Any]
    calculation_details: CalculationDetails
    components: List[BreakdownComponent]
    
    # Drill-down capabilities
    available_groupings: List[GroupingType]
    drill_down_levels: List[DrillDownLevel]
    
    # Metadata
    total_positions: int
    data_freshness: str
    cache_expires: Optional[str] = None

class FilterOptions(BaseModel):
    """Available filtering options for breakdowns"""
    symbols: Optional[List[str]] = None
    strategies: Optional[List[str]] = None
    position_types: Optional[List[str]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_return: Optional[float] = None
    max_return: Optional[float] = None
    expiry_start: Optional[str] = None
    expiry_end: Optional[str] = None

class BreakdownRequest(BaseModel):
    """Request parameters for breakdown data"""
    metric_type: str  # "total_value", "total_return", "greeks", etc.
    grouping: GroupingType = GroupingType.SYMBOL
    sort_by: SortType = SortType.VALUE
    sort_descending: bool = True
    limit: Optional[int] = None
    filters: Optional[FilterOptions] = None
    include_calculation_details: bool = True
    drill_down_level: int = 1

class GreeksBreakdownRequest(BaseModel):
    """Specific request for Greeks breakdown"""
    greek_type: str  # "delta", "gamma", "theta", "vega", "rho"
    grouping: GroupingType = GroupingType.SYMBOL
    sort_by: SortType = SortType.VALUE
    absolute_values: bool = False  # Whether to use absolute values for sorting
    include_portfolio_level: bool = True
    filters: Optional[FilterOptions] = None

class ComparisonRequest(BaseModel):
    """Request for comparing multiple metrics or time periods"""
    primary_metric: str
    comparison_metrics: List[str]
    grouping: GroupingType
    time_periods: Optional[List[str]] = None  # For historical comparison
    
class ExportRequest(BaseModel):
    """Request for exporting breakdown data"""
    breakdown_request: BreakdownRequest
    export_format: str = "csv"  # "csv", "json", "pdf"
    include_positions: bool = True
    include_calculations: bool = False
