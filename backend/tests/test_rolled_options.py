"""
Tests for Rolled Options Chain Analysis

This test suite validates the rolled options chain identification algorithm
and ensures accurate P&L calculations for complex roll sequences.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from typing import Dict, Any, List

from app.services.rolled_options_service import RolledOptionsService, RollTransaction, OptionsChain
from app.services.robinhood_service import RobinhoodService


class TestRolledOptionsChainIdentification:
    """Test the core chain identification logic"""
    
    @pytest.fixture
    def mock_rh_service(self):
        """Create a mock Robinhood service"""
        service = Mock(spec=RobinhoodService)
        service.get_options_orders = AsyncMock()
        service.get_options_positions = AsyncMock()
        return service
    
    @pytest.fixture
    def rolled_options_service(self, mock_rh_service):
        """Create rolled options service with mocked dependencies"""
        return RolledOptionsService(mock_rh_service)
    
    @pytest.fixture
    def sample_roll_orders(self):
        """Sample orders that represent a typical roll sequence"""
        base_time = datetime.now() - timedelta(days=30)
        
        return [
            # First sell to open (initial position)
            {
                "order_id": "order_1",
                "underlying_symbol": "AAPL",
                "strike_price": 150.0,
                "expiration_date": "2024-01-19",
                "option_type": "put",
                "strategy": "SELL PUT",
                "quantity": 1.0,
                "price": 2.50,
                "processed_premium": 250.0,
                "processed_premium_direction": "credit",
                "state": "filled",
                "created_at": (base_time + timedelta(days=1)).isoformat() + "Z"
            },
            # Buy to close (closing original position)
            {
                "order_id": "order_2", 
                "underlying_symbol": "AAPL",
                "strike_price": 150.0,
                "expiration_date": "2024-01-19",
                "option_type": "put",
                "strategy": "BUY TO CLOSE PUT",
                "quantity": 1.0,
                "price": 4.00,
                "processed_premium": 400.0,
                "processed_premium_direction": "debit",
                "state": "filled",
                "created_at": (base_time + timedelta(days=15)).isoformat() + "Z"
            },
            # Sell to open (new position - rolled)
            {
                "order_id": "order_3",
                "underlying_symbol": "AAPL", 
                "strike_price": 145.0,
                "expiration_date": "2024-02-16",
                "option_type": "put",
                "strategy": "SELL PUT",
                "quantity": 1.0,
                "price": 3.50,
                "processed_premium": 350.0,
                "processed_premium_direction": "credit",
                "state": "filled",
                "created_at": (base_time + timedelta(days=15, minutes=30)).isoformat() + "Z"
            },
            # Second roll - buy to close
            {
                "order_id": "order_4",
                "underlying_symbol": "AAPL",
                "strike_price": 145.0,
                "expiration_date": "2024-02-16", 
                "option_type": "put",
                "strategy": "BUY TO CLOSE PUT",
                "quantity": 1.0,
                "price": 2.00,
                "processed_premium": 200.0,
                "processed_premium_direction": "debit",
                "state": "filled",
                "created_at": (base_time + timedelta(days=25)).isoformat() + "Z"
            },
            # Second roll - sell to open
            {
                "order_id": "order_5",
                "underlying_symbol": "AAPL",
                "strike_price": 140.0,
                "expiration_date": "2024-03-15",
                "option_type": "put",
                "strategy": "SELL PUT",
                "quantity": 1.0,
                "price": 2.75,
                "processed_premium": 275.0,
                "processed_premium_direction": "credit",
                "state": "filled",
                "created_at": (base_time + timedelta(days=25, minutes=15)).isoformat() + "Z"
            }
        ]
    
    @pytest.mark.asyncio
    async def test_roll_pair_identification(self, rolled_options_service):
        """Test identification of close/open pairs that form rolls"""
        
        # Valid roll pair: BUY TO CLOSE followed by SELL TO OPEN
        close_order = {
            "strategy": "BUY TO CLOSE PUT",
            "option_type": "put",
            "quantity": 1.0,
            "created_at": "2024-01-15T10:00:00Z"
        }
        
        open_order = {
            "strategy": "SELL PUT", 
            "option_type": "put",
            "quantity": 1.0,
            "created_at": "2024-01-15T10:30:00Z"
        }
        
        is_roll = rolled_options_service._is_roll_pair(close_order, open_order)
        assert is_roll, "Should identify valid close/open pair as roll"
        
        # Invalid: different option types
        invalid_open = open_order.copy()
        invalid_open["option_type"] = "call"
        
        is_not_roll = rolled_options_service._is_roll_pair(close_order, invalid_open)
        assert not is_not_roll, "Should reject pairs with different option types"
        
        # Invalid: too much time between orders (8 days)
        far_open = open_order.copy()
        far_open["created_at"] = "2024-01-23T10:00:00Z"
        
        is_not_roll_time = rolled_options_service._is_roll_pair(close_order, far_open)
        assert not is_not_roll_time, "Should reject pairs with too much time between"
    
    @pytest.mark.asyncio
    async def test_chain_identification_from_orders(self, rolled_options_service, sample_roll_orders, mock_rh_service):
        """Test building a complete chain from order sequence"""
        
        # Mock the orders response
        mock_rh_service.get_options_orders.return_value = {
            "success": True,
            "data": sample_roll_orders
        }
        
        # Mock positions response (chain is still active)
        mock_rh_service.get_options_positions.return_value = {
            "success": True,
            "data": [{
                "underlying_symbol": "AAPL",
                "strike_price": 140.0,
                "expiration_date": "2024-03-15",
                "option_type": "put"
            }]
        }
        
        # Test chain identification
        result = await rolled_options_service.get_rolled_options_chains(days_back=60)
        
        assert result["success"], "Chain identification should succeed"
        chains = result["data"]["chains"]
        assert len(chains) == 1, "Should identify exactly one chain"
        
        chain = chains[0]
        assert chain["underlying_symbol"] == "AAPL"
        assert chain["initial_strategy"] == "SELL_PUT"
        assert chain["total_rolls"] == 2, "Should identify two rolls in the sequence"
        assert chain["status"] == "active", "Chain should be marked as active"
        
        # Verify roll details
        rolls = chain["rolls"]
        assert len(rolls) == 2, "Should have two roll transactions"
        
        # First roll: 150 PUT -> 145 PUT
        first_roll = rolls[0]
        assert first_roll["close_strike"] == 150.0
        assert first_roll["open_strike"] == 145.0
        assert first_roll["strike_direction"] == "down"
        assert first_roll["net_credit"] == -50.0  # 350 collected - 400 paid = -50 (net debit)
        assert first_roll["roll_type"] == "defensive"
        
        # Second roll: 145 PUT -> 140 PUT  
        second_roll = rolls[1]
        assert second_roll["close_strike"] == 145.0
        assert second_roll["open_strike"] == 140.0
        assert second_roll["strike_direction"] == "down"
        assert second_roll["net_credit"] == 75.0  # 275 collected - 200 paid = 75 (net credit)
    
    @pytest.mark.asyncio
    async def test_pnl_calculation(self, rolled_options_service, sample_roll_orders, mock_rh_service):
        """Test P&L calculation for rolled chains"""
        
        mock_rh_service.get_options_orders.return_value = {
            "success": True,
            "data": sample_roll_orders
        }
        
        mock_rh_service.get_options_positions.return_value = {
            "success": True,
            "data": []  # Position closed
        }
        
        result = await rolled_options_service.get_rolled_options_chains(days_back=60)
        chain = result["data"]["chains"][0]
        
        # Expected P&L calculation:
        # Initial credit: +250 (first sell)
        # First roll: -400 (buy to close) + 350 (sell to open) = -50
        # Second roll: -200 (buy to close) + 275 (sell to open) = +75
        # Total realized P&L: 250 - 50 + 75 = 275
        
        expected_realized_pnl = 250.0 + (-50.0) + 75.0  # 275.0
        assert abs(chain["realized_pnl"] - expected_realized_pnl) < 0.01, f"Expected {expected_realized_pnl}, got {chain['realized_pnl']}"
        
        # Since position is closed, unrealized should be 0
        assert chain["unrealized_pnl"] == 0.0, "Closed position should have no unrealized P&L"
        assert chain["total_pnl"] == chain["realized_pnl"], "Total P&L should equal realized for closed position"


class TestRollClassification:
    """Test roll type classification logic"""
    
    @pytest.fixture
    def rolled_options_service(self):
        mock_rh = Mock(spec=RobinhoodService)
        return RolledOptionsService(mock_rh)
    
    def test_defensive_roll_classification(self, rolled_options_service):
        """Test identification of defensive rolls"""
        # Rolling down for a debit (defensive against loss)
        roll_type = rolled_options_service._classify_roll_type(
            strike_direction="down",
            expiry_extension=28,  # days
            net_credit=-50.0     # paid debit
        )
        assert roll_type == "defensive", "Down and out for debit should be defensive"
    
    def test_aggressive_roll_classification(self, rolled_options_service):
        """Test identification of aggressive rolls"""
        # Rolling up for a credit (capturing more premium)
        roll_type = rolled_options_service._classify_roll_type(
            strike_direction="up",
            expiry_extension=21,
            net_credit=75.0  # collected credit
        )
        assert roll_type == "aggressive", "Up and out for credit should be aggressive"
    
    def test_time_roll_classification(self, rolled_options_service):
        """Test identification of time-based rolls"""
        # Rolling out in time only (same strike)
        roll_type = rolled_options_service._classify_roll_type(
            strike_direction="same",
            expiry_extension=35,
            net_credit=25.0
        )
        assert roll_type == "time", "Same strike with time extension should be time roll"


class TestChainStatusDetermination:
    """Test chain status logic (active/closed/expired)"""
    
    @pytest.fixture
    def rolled_options_service(self):
        mock_rh = Mock(spec=RobinhoodService)
        return RolledOptionsService(mock_rh)
    
    @pytest.mark.asyncio
    async def test_active_chain_status(self, rolled_options_service):
        """Test identification of active chains"""
        
        # Mock position that matches the last roll
        last_roll = Mock()
        last_roll.underlying_symbol = "AAPL"
        last_roll.open_strike = 145.0
        last_roll.open_expiry = "2024-12-31"
        
        rolled_options_service.rh_service.get_options_positions = AsyncMock(return_value={
            "success": True,
            "data": [{
                "underlying_symbol": "AAPL",
                "strike_price": 145.0,
                "expiration_date": "2024-12-31"
            }]
        })
        
        status = await rolled_options_service._determine_chain_status("AAPL", last_roll)
        assert status == "active", "Should identify chain as active when matching position exists"
    
    @pytest.mark.asyncio
    async def test_expired_chain_status(self, rolled_options_service):
        """Test identification of expired chains"""
        
        # Mock position with past expiry date
        last_roll = Mock()
        last_roll.underlying_symbol = "AAPL"
        last_roll.open_strike = 145.0
        last_roll.open_expiry = "2023-01-01"  # Past date
        
        rolled_options_service.rh_service.get_options_positions = AsyncMock(return_value={
            "success": True,
            "data": []  # No matching position
        })
        
        status = await rolled_options_service._determine_chain_status("AAPL", last_roll)
        assert status == "expired", "Should identify chain as expired when expiry date is past"
    
    @pytest.mark.asyncio 
    async def test_closed_chain_status(self, rolled_options_service):
        """Test identification of closed chains"""
        
        # Mock position with future expiry but no current position
        last_roll = Mock()
        last_roll.underlying_symbol = "AAPL"
        last_roll.open_strike = 145.0
        last_roll.open_expiry = "2026-01-01"  # Future date
        
        rolled_options_service.rh_service.get_options_positions = AsyncMock(return_value={
            "success": True,
            "data": []  # No matching position
        })
        
        status = await rolled_options_service._determine_chain_status("AAPL", last_roll)
        assert status == "closed", "Should identify chain as closed when no position exists but not expired"


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.fixture
    def rolled_options_service(self):
        mock_rh = Mock(spec=RobinhoodService)
        return RolledOptionsService(mock_rh)
    
    @pytest.mark.asyncio
    async def test_no_orders_found(self, rolled_options_service):
        """Test handling when no orders are found"""
        
        rolled_options_service.rh_service.get_options_orders = AsyncMock(return_value={
            "success": True,
            "data": []
        })
        
        result = await rolled_options_service.get_rolled_options_chains(days_back=30)
        
        assert result["success"], "Should succeed even with no orders"
        assert len(result["data"]["chains"]) == 0, "Should return empty chains list"
        assert result["data"]["summary"]["total_chains"] == 0, "Summary should show zero chains"
    
    @pytest.mark.asyncio
    async def test_single_order_no_rolls(self, rolled_options_service):
        """Test handling of single orders that don't form rolls"""
        
        single_order = [{
            "order_id": "order_1",
            "underlying_symbol": "AAPL",
            "strategy": "SELL PUT",
            "option_type": "put",
            "state": "filled",
            "created_at": "2024-01-15T10:00:00Z"
        }]
        
        rolled_options_service.rh_service.get_options_orders = AsyncMock(return_value={
            "success": True,
            "data": single_order
        })
        
        result = await rolled_options_service.get_rolled_options_chains(days_back=30)
        
        assert result["success"], "Should succeed with single order"
        assert len(result["data"]["chains"]) == 0, "Single order should not create a chain"
    
    def test_invalid_date_handling(self, rolled_options_service):
        """Test handling of invalid date formats"""
        
        # Test with invalid date format
        order1 = {
            "strategy": "BUY TO CLOSE PUT",
            "option_type": "put", 
            "quantity": 1.0,
            "created_at": "invalid-date"
        }
        
        order2 = {
            "strategy": "SELL PUT",
            "option_type": "put",
            "quantity": 1.0, 
            "created_at": "2024-01-15T10:00:00Z"
        }
        
        # Should not crash on invalid date, but should return False
        is_roll = rolled_options_service._is_roll_pair(order1, order2)
        assert not is_roll, "Should handle invalid dates gracefully"
    
    def test_quantity_mismatch_handling(self, rolled_options_service):
        """Test handling of quantity mismatches in roll pairs"""
        
        close_order = {
            "strategy": "BUY TO CLOSE PUT",
            "option_type": "put",
            "quantity": 1.0,  # 1 contract
            "created_at": "2024-01-15T10:00:00Z"
        }
        
        open_order = {
            "strategy": "SELL PUT",
            "option_type": "put", 
            "quantity": 5.0,  # 5 contracts (>20% difference)
            "created_at": "2024-01-15T10:30:00Z"
        }
        
        is_roll = rolled_options_service._is_roll_pair(close_order, open_order)
        assert not is_roll, "Should reject pairs with significant quantity differences"


class TestDocumentationExamples:
    """Test the examples provided in documentation"""
    
    @pytest.mark.asyncio
    async def test_typical_put_selling_roll_sequence(self):
        """
        Test a typical put selling strategy with rolls
        
        Example from documentation:
        1. Sell AAPL 150 PUT for $2.50 credit
        2. Stock drops, roll down to 145 PUT for net $0.50 debit
        3. Time passes, roll to 140 PUT for $0.75 credit
        """
        
        mock_rh = Mock(spec=RobinhoodService)
        service = RolledOptionsService(mock_rh)
        
        # Create the documented example orders
        orders = [
            {
                "order_id": "doc_1",
                "underlying_symbol": "AAPL",
                "strike_price": 150.0,
                "expiration_date": "2024-01-19",
                "option_type": "put",
                "strategy": "SELL PUT",
                "quantity": 1.0,
                "processed_premium": 250.0,
                "processed_premium_direction": "credit",
                "state": "filled",
                "created_at": "2024-01-01T10:00:00Z"
            },
            {
                "order_id": "doc_2", 
                "underlying_symbol": "AAPL",
                "strike_price": 150.0,
                "expiration_date": "2024-01-19",
                "option_type": "put",
                "strategy": "BUY TO CLOSE PUT",
                "quantity": 1.0,
                "processed_premium": 300.0,
                "processed_premium_direction": "debit", 
                "state": "filled",
                "created_at": "2024-01-10T10:00:00Z"
            },
            {
                "order_id": "doc_3",
                "underlying_symbol": "AAPL",
                "strike_price": 145.0,
                "expiration_date": "2024-02-16", 
                "option_type": "put",
                "strategy": "SELL PUT",
                "quantity": 1.0,
                "processed_premium": 250.0,
                "processed_premium_direction": "credit",
                "state": "filled", 
                "created_at": "2024-01-10T10:30:00Z"
            },
            {
                "order_id": "doc_4",
                "underlying_symbol": "AAPL",
                "strike_price": 145.0,
                "expiration_date": "2024-02-16",
                "option_type": "put", 
                "strategy": "BUY TO CLOSE PUT",
                "quantity": 1.0,
                "processed_premium": 175.0,
                "processed_premium_direction": "debit",
                "state": "filled",
                "created_at": "2024-01-20T10:00:00Z"
            },
            {
                "order_id": "doc_5",
                "underlying_symbol": "AAPL",
                "strike_price": 140.0,
                "expiration_date": "2024-03-15",
                "option_type": "put",
                "strategy": "SELL PUT", 
                "quantity": 1.0,
                "processed_premium": 250.0,
                "processed_premium_direction": "credit",
                "state": "filled",
                "created_at": "2024-01-20T10:15:00Z"
            }
        ]
        
        mock_rh.get_options_orders = AsyncMock(return_value={
            "success": True,
            "data": orders
        })
        
        mock_rh.get_options_positions = AsyncMock(return_value={
            "success": True,
            "data": []
        })
        
        result = await service.get_rolled_options_chains(days_back=90)
        
        assert result["success"], "Documentation example should be parsed successfully"
        chains = result["data"]["chains"]
        assert len(chains) == 1, "Should identify one chain from documentation example"
        
        chain = chains[0]
        assert chain["total_rolls"] == 2, "Should identify two rolls"
        
        # Verify P&L matches documentation
        # Roll 1: 250 credit - 300 debit + 250 credit = 200 net
        # Roll 2: -175 debit + 250 credit = 75 net  
        # Total: 250 (initial) + 200 + 75 = 525? Let me recalculate...
        # Actually: Initial 250, Roll 1 net (-300+250=-50), Roll 2 net (-175+250=75)
        # Total realized: 250 + (-50) + 75 = 275
        
        expected_total_pnl = 275.0
        assert abs(chain["total_pnl"] - expected_total_pnl) < 1.0, f"P&L should match documentation example: expected {expected_total_pnl}, got {chain['total_pnl']}"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])