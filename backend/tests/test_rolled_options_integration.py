#!/usr/bin/env python3
"""
Integration tests for rolled options logic

This module provides comprehensive integration testing for the rolled options
chain identification system, including end-to-end workflow validation.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from app.services.rolled_options_service import RolledOptionsService

class TestRolledOptionsIntegration:
    """Integration tests for rolled options chain detection"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_chain_detection(self):
        """Test complete end-to-end chain detection workflow"""
        
        # Create mock service
        mock_rh = Mock()
        service = RolledOptionsService(mock_rh)
        
        # Test roll pair identification
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
        
        is_roll = service._is_roll_pair(close_order, open_order)
        assert is_roll, "Should identify valid close/open pair as roll"
        
        # Test sample orders representing a realistic trading scenario
        base_time = datetime.now() - timedelta(days=30)
        
        sample_orders = [
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
        }
    ]
    
        # Validate pattern finding
        roll_patterns = service._find_roll_patterns(sample_orders)
        assert len(roll_patterns) == 3, f"Expected 3 orders in roll pattern, got {len(roll_patterns)}"
        
        # Validate chain building
        chain = await service._build_chain_from_orders("AAPL", "SELL_PUT", roll_patterns)
        assert chain is not None, "Should successfully build chain from roll patterns"
        assert chain.total_rolls == 1, f"Expected 1 roll, got {chain.total_rolls}"
        assert chain.underlying_symbol == "AAPL", "Chain should be for AAPL"
        
        # Mock the service calls for full integration test
        mock_rh.get_options_orders = AsyncMock(return_value={
            "success": True,
            "data": sample_orders
        })
        
        mock_rh.get_options_positions = AsyncMock(return_value={
            "success": True,
            "data": [{
                "underlying_symbol": "AAPL", 
                "strike_price": 145.0,
                "expiration_date": "2024-02-16",
                "option_type": "put"
            }]
        })
        
        # Test full end-to-end chain identification
        result = await service.get_rolled_options_chains(days_back=60)
        assert result["success"], "Chain identification should succeed"
        
        chains = result["data"]["chains"]
        assert len(chains) == 1, f"Expected 1 chain, got {len(chains)}"
        
        chain_data = chains[0]
        assert chain_data["underlying_symbol"] == "AAPL"
        assert chain_data["initial_strategy"] == "SELL_PUT"
        assert chain_data["total_rolls"] == 1
        assert chain_data["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_multiple_chains_scenario(self):
        """Test scenario with multiple separate chains"""
        
        mock_rh = Mock()
        service = RolledOptionsService(mock_rh)
        
        base_time = datetime.now() - timedelta(days=60)
        
        # Two separate chains: AAPL puts and MSFT calls
        multiple_chain_orders = [
            # AAPL PUT chain
            {
                "order_id": "aapl_1",
                "underlying_symbol": "AAPL",
                "strategy": "SELL PUT",
                "option_type": "put",
                "strike_price": 150.0,
                "quantity": 1.0,
                "processed_premium": 250.0,
                "processed_premium_direction": "credit",
                "state": "filled",
                "created_at": (base_time + timedelta(days=1)).isoformat() + "Z"
            },
            {
                "order_id": "aapl_2", 
                "underlying_symbol": "AAPL",
                "strategy": "BUY TO CLOSE PUT",
                "option_type": "put",
                "strike_price": 150.0,
                "quantity": 1.0,
                "processed_premium": 100.0,
                "processed_premium_direction": "debit",
                "state": "filled",
                "created_at": (base_time + timedelta(days=15)).isoformat() + "Z"
            },
            {
                "order_id": "aapl_3",
                "underlying_symbol": "AAPL",
                "strategy": "SELL PUT", 
                "option_type": "put",
                "strike_price": 145.0,
                "quantity": 1.0,
                "processed_premium": 200.0,
                "processed_premium_direction": "credit",
                "state": "filled",
                "created_at": (base_time + timedelta(days=15, minutes=30)).isoformat() + "Z"
            },
            # MSFT CALL chain
            {
                "order_id": "msft_1",
                "underlying_symbol": "MSFT",
                "strategy": "SELL CALL",
                "option_type": "call",
                "strike_price": 300.0,
                "quantity": 2.0,
                "processed_premium": 400.0,
                "processed_premium_direction": "credit",
                "state": "filled",
                "created_at": (base_time + timedelta(days=20)).isoformat() + "Z"
            },
            {
                "order_id": "msft_2",
                "underlying_symbol": "MSFT", 
                "strategy": "BUY TO CLOSE CALL",
                "option_type": "call",
                "strike_price": 300.0,
                "quantity": 2.0,
                "processed_premium": 600.0,
                "processed_premium_direction": "debit",
                "state": "filled",
                "created_at": (base_time + timedelta(days=30)).isoformat() + "Z"
            },
            {
                "order_id": "msft_3",
                "underlying_symbol": "MSFT",
                "strategy": "SELL CALL",
                "option_type": "call", 
                "strike_price": 310.0,
                "quantity": 2.0,
                "processed_premium": 300.0,
                "processed_premium_direction": "credit",
                "state": "filled",
                "created_at": (base_time + timedelta(days=30, minutes=15)).isoformat() + "Z"
            }
        ]
        
        mock_rh.get_options_orders = AsyncMock(return_value={
            "success": True,
            "data": multiple_chain_orders
        })
        
        mock_rh.get_options_positions = AsyncMock(return_value={
            "success": True,
            "data": []  # All positions closed
        })
        
        result = await service.get_rolled_options_chains(days_back=90)
        assert result["success"], "Should successfully identify multiple chains"
        
        chains = result["data"]["chains"]
        assert len(chains) == 2, f"Expected 2 chains, got {len(chains)}"
        
        # Verify chains are for different symbols
        symbols = {chain["underlying_symbol"] for chain in chains}
        assert symbols == {"AAPL", "MSFT"}, f"Expected AAPL and MSFT chains, got {symbols}"
        
        # Verify chain details
        for chain in chains:
            assert chain["total_rolls"] == 1, "Each chain should have 1 roll"
            assert chain["status"] == "closed", "All chains should be closed"


async def debug_test():
    """Legacy debug function for manual testing"""
    test_instance = TestRolledOptionsIntegration()
    await test_instance.test_end_to_end_chain_detection()
    print("✅ End-to-end test passed!")
    
    await test_instance.test_multiple_chains_scenario()
    print("✅ Multiple chains test passed!")
    
    print("🎉 All integration tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(debug_test())