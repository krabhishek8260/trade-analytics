"""
Portfolio Breakdown Calculation Service

This service provides detailed breakdowns of portfolio metrics with drill-down
capabilities, calculation transparency, and data slicing functionality.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict

from app.schemas.breakdown import (
    BreakdownResponse, BreakdownComponent, CalculationDetails, 
    CalculationStep, DrillDownLevel, PositionBreakdown,
    GroupingType, SortType, FilterOptions, BreakdownRequest
)
from app.services.robinhood_service import RobinhoodService

logger = logging.getLogger(__name__)

class BreakdownCalculator:
    """Calculator for detailed portfolio metric breakdowns"""
    
    def __init__(self, robinhood_service: RobinhoodService):
        self.rh_service = robinhood_service
    
    async def calculate_total_value_breakdown(self, request: BreakdownRequest) -> BreakdownResponse:
        """Calculate detailed breakdown for portfolio total value"""
        
        # Get positions data
        positions_result = await self.rh_service.get_options_positions()
        if not positions_result.get("success", False):
            raise ValueError("Failed to fetch positions data")
        
        positions = positions_result["data"]
        
        # Calculate main totals
        total_long_value = sum(pos["market_value"] for pos in positions if pos["position_type"] == "long")
        total_short_value = sum(pos["market_value"] for pos in positions if pos["position_type"] == "short")
        net_portfolio_value = total_long_value - total_short_value
        
        # Create calculation details
        calculation_details = self._create_total_value_calculation_details(
            total_long_value, total_short_value, net_portfolio_value
        )
        
        # Group components based on request
        components = self._group_positions_for_breakdown(
            positions, request.grouping, "total_value"
        )
        
        # Sort components
        components = self._sort_components(components, request.sort_by, request.sort_descending)
        
        # Apply filters if provided
        if request.filters:
            components = self._apply_filters(components, request.filters)
        
        # Create drill-down levels
        drill_down_levels = self._create_drill_down_levels(positions, request.grouping)
        
        return BreakdownResponse(
            metric_name="total_value",
            metric_display_name="Portfolio Total Value", 
            total_value=net_portfolio_value,
            calculation_method="Net Assets - Liabilities",
            last_updated=datetime.utcnow().isoformat(),
            summary={
                "long_positions_value": total_long_value,
                "short_positions_value": total_short_value,
                "net_value": net_portfolio_value,
                "total_positions": len(positions),
                "long_positions": len([p for p in positions if p["position_type"] == "long"]),
                "short_positions": len([p for p in positions if p["position_type"] == "short"])
            },
            calculation_details=calculation_details,
            components=components,
            available_groupings=[GroupingType.SYMBOL, GroupingType.STRATEGY, GroupingType.EXPIRY, GroupingType.POSITION_TYPE],
            drill_down_levels=drill_down_levels,
            total_positions=len(positions),
            data_freshness="real-time"
        )
    
    async def calculate_total_return_breakdown(self, request: BreakdownRequest) -> BreakdownResponse:
        """Calculate detailed breakdown for portfolio total return"""
        
        positions_result = await self.rh_service.get_options_positions()
        if not positions_result.get("success", False):
            raise ValueError("Failed to fetch positions data")
        
        positions = positions_result["data"]
        
        # Calculate totals
        total_return = sum(pos["total_return"] for pos in positions)
        total_cost = sum(abs(pos["total_cost"]) for pos in positions)
        return_percentage = (total_return / total_cost * 100) if total_cost > 0 else 0
        
        # Winners and losers
        winners = [pos for pos in positions if pos["total_return"] > 0]
        losers = [pos for pos in positions if pos["total_return"] < 0]
        neutral = [pos for pos in positions if pos["total_return"] == 0]
        
        # Create calculation details
        calculation_details = self._create_total_return_calculation_details(
            total_return, total_cost, return_percentage, len(winners), len(losers)
        )
        
        # Group components
        components = self._group_positions_for_breakdown(
            positions, request.grouping, "total_return"
        )
        
        # Sort and filter
        components = self._sort_components(components, request.sort_by, request.sort_descending)
        if request.filters:
            components = self._apply_filters(components, request.filters)
        
        drill_down_levels = self._create_drill_down_levels(positions, request.grouping)
        
        return BreakdownResponse(
            metric_name="total_return",
            metric_display_name="Portfolio Total Return",
            total_value=total_return,
            calculation_method="Sum of Individual Position P&L",
            last_updated=datetime.utcnow().isoformat(),
            summary={
                "total_return": total_return,
                "return_percentage": return_percentage,
                "winners": len(winners),
                "losers": len(losers),
                "neutral": len(neutral),
                "win_rate": (len(winners) / len(positions) * 100) if positions else 0,
                "average_return": total_return / len(positions) if positions else 0
            },
            calculation_details=calculation_details,
            components=components,
            available_groupings=[GroupingType.SYMBOL, GroupingType.STRATEGY, GroupingType.EXPIRY, GroupingType.POSITION_TYPE],
            drill_down_levels=drill_down_levels,
            total_positions=len(positions),
            data_freshness="real-time"
        )
    
    async def calculate_greeks_breakdown(self, greek_type: str, request: BreakdownRequest) -> BreakdownResponse:
        """Calculate detailed breakdown for portfolio Greeks"""
        
        greeks_result = await self.rh_service.get_portfolio_greeks()
        if not greeks_result.get("success", False):
            raise ValueError("Failed to fetch Greeks data")
        
        positions_result = await self.rh_service.get_options_positions()
        if not positions_result.get("success", False):
            raise ValueError("Failed to fetch positions data")
        
        portfolio_greeks = greeks_result["data"]
        positions = positions_result["data"]
        
        # Get the specific Greek value
        greek_value = portfolio_greeks.get(f"net_{greek_type}", 0)
        
        # Create calculation details
        calculation_details = self._create_greeks_calculation_details(greek_type, greek_value, positions)
        
        # Group by Greek contributions
        components = self._group_positions_for_greeks_breakdown(
            positions, request.grouping, greek_type
        )
        
        # Sort and filter
        components = self._sort_components(components, request.sort_by, request.sort_descending)
        if request.filters:
            components = self._apply_filters(components, request.filters)
        
        drill_down_levels = self._create_drill_down_levels(positions, request.grouping)
        
        return BreakdownResponse(
            metric_name=f"{greek_type}_breakdown",
            metric_display_name=f"Portfolio {greek_type.title()} Breakdown",
            total_value=greek_value,
            calculation_method=f"Sum of Position {greek_type.title()} Values",
            last_updated=datetime.utcnow().isoformat(),
            summary={
                f"net_{greek_type}": greek_value,
                "portfolio_greeks": portfolio_greeks,
                "total_positions": len(positions)
            },
            calculation_details=calculation_details,
            components=components,
            available_groupings=[GroupingType.SYMBOL, GroupingType.STRATEGY, GroupingType.POSITION_TYPE],
            drill_down_levels=drill_down_levels,
            total_positions=len(positions),
            data_freshness="real-time"
        )
    
    def _create_total_value_calculation_details(self, long_value: float, short_value: float, net_value: float) -> CalculationDetails:
        """Create detailed calculation explanation for total value"""
        
        calculation_steps = [
            CalculationStep(
                step_number=1,
                description="Calculate total value of long positions (assets)",
                formula="Sum(long_position_market_values)",
                values={"long_positions_value": long_value},
                result=long_value
            ),
            CalculationStep(
                step_number=2,
                description="Calculate total value of short positions (liabilities)",
                formula="Sum(short_position_market_values)",
                values={"short_positions_value": short_value},
                result=short_value
            ),
            CalculationStep(
                step_number=3,
                description="Calculate net portfolio value",
                formula="Long Assets - Short Liabilities",
                values={
                    "long_assets": long_value,
                    "short_liabilities": short_value
                },
                result=net_value
            )
        ]
        
        return CalculationDetails(
            metric_name="Portfolio Total Value",
            final_formula="Assets - Liabilities",
            explanation="Net portfolio value calculated by subtracting short position liabilities from long position assets",
            example=f"${long_value:,.2f} (long assets) - ${short_value:,.2f} (short liabilities) = ${net_value:,.2f}",
            calculation_steps=calculation_steps,
            components_used=["market_value", "position_type"],
            methodology_notes=[
                "Long positions represent assets you can sell",
                "Short positions represent liabilities you must close",
                "Net value shows true portfolio worth"
            ]
        )
    
    def _create_total_return_calculation_details(self, total_return: float, total_cost: float, 
                                                return_pct: float, winners: int, losers: int) -> CalculationDetails:
        """Create detailed calculation explanation for total return"""
        
        calculation_steps = [
            CalculationStep(
                step_number=1,
                description="Sum all individual position P&L",
                formula="Sum(position_total_returns)",
                values={"total_return": total_return},
                result=total_return
            ),
            CalculationStep(
                step_number=2,
                description="Calculate total cost basis",
                formula="Sum(abs(position_costs))",
                values={"total_cost": total_cost},
                result=total_cost
            ),
            CalculationStep(
                step_number=3,
                description="Calculate return percentage",
                formula="(Total Return / Total Cost) × 100",
                values={
                    "total_return": total_return,
                    "total_cost": total_cost
                },
                result=return_pct
            )
        ]
        
        return CalculationDetails(
            metric_name="Portfolio Total Return",
            final_formula="Sum(Individual Position P&L)",
            explanation="Total portfolio profit/loss from all options positions",
            example=f"${total_return:,.2f} return on ${total_cost:,.2f} cost basis = {return_pct:.2f}%",
            calculation_steps=calculation_steps,
            components_used=["total_return", "total_cost"],
            methodology_notes=[
                f"{winners} winning positions contributing to gains",
                f"{losers} losing positions reducing gains",
                "Return percentage based on absolute cost basis"
            ]
        )
    
    def _create_greeks_calculation_details(self, greek_type: str, greek_value: float, positions: List[Dict]) -> CalculationDetails:
        """Create detailed calculation explanation for Greeks"""
        
        calculation_steps = [
            CalculationStep(
                step_number=1,
                description=f"Sum all position {greek_type} values",
                formula=f"Sum(position_{greek_type} × contracts × multiplier)",
                values={f"portfolio_{greek_type}": greek_value},
                result=greek_value
            )
        ]
        
        return CalculationDetails(
            metric_name=f"Portfolio {greek_type.title()}",
            final_formula=f"Sum(Position {greek_type.title()} × Size)",
            explanation=f"Portfolio-level {greek_type} exposure from all options positions",
            example=f"Portfolio {greek_type}: {greek_value:.4f}",
            calculation_steps=calculation_steps,
            components_used=["greeks", "contracts", "position_type"],
            methodology_notes=[
                f"{greek_type.title()} measures price sensitivity",
                "Values adjusted for position size and direction",
                "Positive/negative values indicate exposure direction"
            ]
        )
    
    def _group_positions_for_breakdown(self, positions: List[Dict], grouping: GroupingType, 
                                     metric_type: str) -> List[BreakdownComponent]:
        """Group positions for breakdown based on grouping type"""
        
        groups = defaultdict(list)
        
        # Group positions
        for position in positions:
            if grouping == GroupingType.SYMBOL:
                key = position.get("underlying_symbol", "UNKNOWN")
            elif grouping == GroupingType.STRATEGY:
                key = position.get("strategy", "UNKNOWN")
            elif grouping == GroupingType.POSITION_TYPE:
                key = position.get("position_type", "unknown")
            elif grouping == GroupingType.EXPIRY:
                key = position.get("expiration_date", "unknown")
            else:
                key = "ALL"
            
            groups[key].append(position)
        
        # Create breakdown components
        components = []
        total_value = sum(pos.get(metric_type, 0) for pos in positions)
        
        for group_name, group_positions in groups.items():
            component_value = sum(pos.get(metric_type, 0) for pos in group_positions)
            percentage = (component_value / total_value * 100) if total_value != 0 else 0
            
            # Create position breakdowns
            position_breakdowns = [
                PositionBreakdown(
                    position_id=pos.get("id", ""),
                    underlying_symbol=pos.get("underlying_symbol", ""),
                    option_type=pos.get("option_type", ""),
                    strike_price=pos.get("strike_price", 0),
                    expiration_date=pos.get("expiration_date", ""),
                    contracts=pos.get("contracts", 0),
                    market_value=pos.get("market_value", 0),
                    total_cost=pos.get("total_cost", 0),
                    total_return=pos.get("total_return", 0),
                    percent_change=pos.get("percent_change", 0),
                    strategy=pos.get("strategy", "")
                )
                for pos in group_positions
            ]
            
            component = BreakdownComponent(
                id=f"{grouping.value}_{group_name}",
                name=group_name,
                display_name=group_name,
                value=component_value,
                percentage=percentage,
                position_count=len(group_positions),
                component_type=grouping.value,
                positions=position_breakdowns,
                total_return=sum(pos.get("total_return", 0) for pos in group_positions),
                return_percentage=percentage,
                market_value=sum(pos.get("market_value", 0) for pos in group_positions),
                cost_basis=sum(abs(pos.get("total_cost", 0)) for pos in group_positions)
            )
            
            if grouping == GroupingType.SYMBOL:
                component.underlying_symbol = group_name
            elif grouping == GroupingType.STRATEGY:
                component.strategy = group_name
            
            components.append(component)
        
        return components
    
    def _group_positions_for_greeks_breakdown(self, positions: List[Dict], grouping: GroupingType, 
                                            greek_type: str) -> List[BreakdownComponent]:
        """Group positions for Greeks breakdown"""
        
        groups = defaultdict(list)
        
        for position in positions:
            if grouping == GroupingType.SYMBOL:
                key = position.get("underlying_symbol", "UNKNOWN")
            elif grouping == GroupingType.STRATEGY:
                key = position.get("strategy", "UNKNOWN")
            elif grouping == GroupingType.POSITION_TYPE:
                key = position.get("position_type", "unknown")
            else:
                key = "ALL"
            
            groups[key].append(position)
        
        components = []
        
        for group_name, group_positions in groups.items():
            # Calculate Greek contribution for this group
            greek_contribution = 0
            for pos in group_positions:
                greeks = pos.get("greeks", {})
                position_greek = greeks.get(greek_type, 0)
                contracts = pos.get("contracts", 0)
                
                # Adjust for position type and size
                if pos.get("position_type") == "short":
                    position_greek = -position_greek
                
                greek_contribution += position_greek * contracts * 100
            
            # Create position breakdowns
            position_breakdowns = [
                PositionBreakdown(
                    position_id=pos.get("id", ""),
                    underlying_symbol=pos.get("underlying_symbol", ""),
                    option_type=pos.get("option_type", ""),
                    strike_price=pos.get("strike_price", 0),
                    expiration_date=pos.get("expiration_date", ""),
                    contracts=pos.get("contracts", 0),
                    market_value=pos.get("market_value", 0),
                    total_cost=pos.get("total_cost", 0),
                    total_return=pos.get("total_return", 0),
                    percent_change=pos.get("percent_change", 0),
                    strategy=pos.get("strategy", "")
                )
                for pos in group_positions
            ]
            
            component = BreakdownComponent(
                id=f"{grouping.value}_{group_name}_{greek_type}",
                name=group_name,
                display_name=f"{group_name} {greek_type.title()}",
                value=greek_contribution,
                percentage=0,  # Will calculate after we have total
                position_count=len(group_positions),
                component_type=f"{grouping.value}_{greek_type}",
                positions=position_breakdowns,
                total_return=sum(pos.get("total_return", 0) for pos in group_positions),
                return_percentage=0,
                market_value=sum(pos.get("market_value", 0) for pos in group_positions),
                cost_basis=sum(abs(pos.get("total_cost", 0)) for pos in group_positions)
            )
            
            components.append(component)
        
        return components
    
    def _sort_components(self, components: List[BreakdownComponent], 
                        sort_by: SortType, descending: bool) -> List[BreakdownComponent]:
        """Sort breakdown components"""
        
        if sort_by == SortType.VALUE:
            key_func = lambda x: x.value
        elif sort_by == SortType.RETURN:
            key_func = lambda x: x.total_return
        elif sort_by == SortType.PERCENTAGE:
            key_func = lambda x: x.percentage
        elif sort_by == SortType.ALPHABETICAL:
            key_func = lambda x: x.name.lower()
        else:
            key_func = lambda x: x.value
        
        return sorted(components, key=key_func, reverse=descending)
    
    def _apply_filters(self, components: List[BreakdownComponent], 
                      filters: FilterOptions) -> List[BreakdownComponent]:
        """Apply filters to breakdown components"""
        
        filtered = components
        
        if filters.symbols:
            filtered = [c for c in filtered if c.underlying_symbol in filters.symbols]
        
        if filters.strategies:
            filtered = [c for c in filtered if c.strategy in filters.strategies]
        
        if filters.min_value is not None:
            filtered = [c for c in filtered if c.value >= filters.min_value]
        
        if filters.max_value is not None:
            filtered = [c for c in filtered if c.value <= filters.max_value]
        
        if filters.min_return is not None:
            filtered = [c for c in filtered if c.total_return >= filters.min_return]
        
        if filters.max_return is not None:
            filtered = [c for c in filtered if c.total_return <= filters.max_return]
        
        return filtered
    
    def _create_drill_down_levels(self, positions: List[Dict], current_grouping: GroupingType) -> List[DrillDownLevel]:
        """Create available drill-down levels"""
        
        levels = []
        
        if current_grouping != GroupingType.SYMBOL:
            symbol_groups = len(set(pos.get("underlying_symbol", "UNKNOWN") for pos in positions))
            levels.append(DrillDownLevel(
                level=1,
                name="By Symbol",
                description="Breakdown by underlying symbol",
                grouping=GroupingType.SYMBOL,
                total_groups=symbol_groups,
                data=[]
            ))
        
        if current_grouping != GroupingType.STRATEGY:
            strategy_groups = len(set(pos.get("strategy", "UNKNOWN") for pos in positions))
            levels.append(DrillDownLevel(
                level=2,
                name="By Strategy",
                description="Breakdown by options strategy",
                grouping=GroupingType.STRATEGY,
                total_groups=strategy_groups,
                data=[]
            ))
        
        if current_grouping != GroupingType.POSITION_TYPE:
            levels.append(DrillDownLevel(
                level=3,
                name="By Position Type",
                description="Breakdown by long/short positions",
                grouping=GroupingType.POSITION_TYPE,
                total_groups=2,
                data=[]
            ))
        
        return levels