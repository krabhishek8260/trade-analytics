"""
Test compatibility between old file-based and new database-based chain detection.
Ensures migration maintains existing behavior while adding strategy code detection.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, date
from decimal import Decimal
import uuid

from app.services.rolled_options_chain_detector import RolledOptionsChainDetector
from app.services.options_order_service import OptionsOrderService
from app.models.options_order import OptionsOrder
from app.models.rolled_options_chain import RolledOptionsChain


@pytest.fixture
def mock_options_service():
    """Mock OptionsOrderService for testing."""
    service = AsyncMock(spec=OptionsOrderService)
    return service


@pytest.fixture
def detector(mock_options_service):
    """Chain detector with mocked options service."""
    return RolledOptionsChainDetector(mock_options_service)


@pytest.fixture
def sample_database_orders():
    """Sample database orders with strategy codes for testing."""
    base_time = datetime(2025, 1, 28, 15, 19, 9)
    user_id = uuid.UUID("12345678-1234-5678-9012-123456789012")
    
    return [
        # Chain 1: Strategy code based (NVDA)
        OptionsOrder(
            id=uuid.uuid4(),
            user_id=user_id,
            order_id="nvda-order-1",
            state="filled",
            chain_symbol="NVDA",
            processed_quantity=Decimal("2.0"),
            processed_premium=Decimal("6310.0"),
            direction="debit",
            side="buy",
            position_effect="open",
            option_type="call",
            strike_price=Decimal("100.0"),
            expiration_date="2025-09-19",
            created_at=base_time,
            long_strategy_code="nvda-strategy-123_L1",
            short_strategy_code="nvda-strategy-123_S1",
            legs_details=[{
                "long_strategy_code": "nvda-strategy-123_L1",
                "short_strategy_code": "nvda-strategy-123_S1",
                "side": "buy",
                "position_effect": "open",
                "option_type": "call",
                "strike_price": "100.0",
                "expiration_date": "2025-09-19"
            }]
        ),
        OptionsOrder(
            id=uuid.uuid4(),
            user_id=user_id,
            order_id="nvda-order-2",
            state="filled",
            chain_symbol="NVDA",
            processed_quantity=Decimal("2.0"),
            processed_premium=Decimal("13050.0"),
            direction="credit",
            side="sell",
            position_effect="close",
            option_type="call",
            strike_price=Decimal("100.0"),
            expiration_date="2025-09-19",
            created_at=base_time.replace(month=7),
            long_strategy_code="nvda-strategy-123_L1",
            short_strategy_code="nvda-strategy-123_S1",
            legs_details=[{
                "long_strategy_code": "nvda-strategy-123_L1",
                "short_strategy_code": "nvda-strategy-123_S1",
                "side": "sell",
                "position_effect": "close",
                "option_type": "call",
                "strike_price": "100.0",
                "expiration_date": "2025-09-19"
            }]
        ),
        
        # Chain 2: Heuristic based (AAPL) - no strategy codes
        OptionsOrder(
            id=uuid.uuid4(),
            user_id=user_id,
            order_id="aapl-order-1",
            state="filled",
            chain_symbol="AAPL",
            processed_quantity=Decimal("1.0"),
            processed_premium=Decimal("500.0"),
            direction="debit",
            side="buy",
            position_effect="open",
            option_type="call",
            strike_price=Decimal("150.0"),
            expiration_date="2025-03-21",
            created_at=base_time,
            strategy="long_call",
            form_source="option_chain",
            long_strategy_code=None,
            short_strategy_code=None,
            legs_details=[{
                "long_strategy_code": None,
                "short_strategy_code": None,
                "side": "buy",
                "position_effect": "open",
                "option_type": "call",
                "strike_price": "150.0",
                "expiration_date": "2025-03-21"
            }]
        ),
        OptionsOrder(
            id=uuid.uuid4(),
            user_id=user_id,
            order_id="aapl-order-2",
            state="filled",
            chain_symbol="AAPL",
            processed_quantity=Decimal("1.0"),
            processed_premium=Decimal("750.0"),
            direction="credit",
            side="sell",
            position_effect="close",
            option_type="call",
            strike_price=Decimal("150.0"),
            expiration_date="2025-03-21",
            created_at=base_time.replace(day=30),
            strategy="short_call",
            form_source="option_chain",
            long_strategy_code=None,
            short_strategy_code=None,
            legs_details=[{
                "long_strategy_code": None,
                "short_strategy_code": None,
                "side": "sell",
                "position_effect": "close",
                "option_type": "call",
                "strike_price": "150.0",
                "expiration_date": "2025-03-21"
            }]
        ),
        
        # Chain 3: Multi-leg roll (TSLA)
        OptionsOrder(
            id=uuid.uuid4(),
            user_id=user_id,
            order_id="tsla-roll-1",
            state="filled",
            chain_symbol="TSLA",
            processed_quantity=Decimal("1.0"),
            processed_premium=Decimal("200.0"),
            direction="credit",
            strategy="roll",
            form_source="strategy_roll",
            created_at=base_time,
            legs_count=2,
            long_strategy_code=None,
            short_strategy_code=None,
            legs_details=[
                {
                    "side": "sell",
                    "position_effect": "close",
                    "option_type": "call",
                    "strike_price": "200.0",
                    "expiration_date": "2025-02-21"
                },
                {
                    "side": "buy", 
                    "position_effect": "open",
                    "option_type": "call",
                    "strike_price": "200.0",
                    "expiration_date": "2025-03-21"
                }
            ]
        )
    ]


@pytest.fixture 
def legacy_file_orders():
    """Sample file-based orders matching legacy format."""
    return [
        {
            "id": "aapl-legacy-1",
            "state": "filled",
            "chain_symbol": "AAPL",
            "processed_quantity": 1.0,
            "processed_premium": 500.0,
            "direction": "debit",
            "strategy": "long_call",
            "form_source": "option_chain",
            "created_at": "2025-01-28T15:19:09.332766Z",
            "legs": [{
                "side": "buy",
                "position_effect": "open", 
                "option_type": "call",
                "strike_price": "150.0",
                "expiration_date": "2025-03-21",
                "long_strategy_code": "",
                "short_strategy_code": ""
            }]
        },
        {
            "id": "aapl-legacy-2", 
            "state": "filled",
            "chain_symbol": "AAPL",
            "processed_quantity": 1.0,
            "processed_premium": 750.0,
            "direction": "credit",
            "strategy": "short_call",
            "form_source": "option_chain",
            "created_at": "2025-01-30T15:19:09.332766Z",
            "legs": [{
                "side": "sell",
                "position_effect": "close",
                "option_type": "call", 
                "strike_price": "150.0",
                "expiration_date": "2025-03-21",
                "long_strategy_code": "",
                "short_strategy_code": ""
            }]
        }
    ]


class TestChainDetectionCompatibility:
    """Test compatibility between database and file-based chain detection."""
    
    @pytest.mark.asyncio
    async def test_strategy_code_detection_priority(self, detector, sample_database_orders):
        """Test that strategy codes take priority over heuristic detection."""
        # Mock database query to return orders with strategy codes
        detector.options_service.get_orders_for_chain_detection.return_value = sample_database_orders[:2]  # NVDA orders
        
        chains = await detector.detect_chains_from_database()
        
        # Should detect NVDA chain using strategy codes
        nvda_chains = [c for c in chains if c.chain_symbol == "NVDA"]
        assert len(nvda_chains) == 1
        
        nvda_chain = nvda_chains[0]
        assert nvda_chain.strategy_code == "nvda-strategy-123_L1"
        assert nvda_chain.total_orders == 2
        assert nvda_chain.net_premium == Decimal("6740.0")  # 13050 - 6310
        assert nvda_chain.detection_method == "strategy_code"
        
    @pytest.mark.asyncio 
    async def test_heuristic_fallback_detection(self, detector, sample_database_orders):
        """Test heuristic detection when strategy codes are missing."""
        # Mock database query to return orders without strategy codes
        detector.options_service.get_orders_for_chain_detection.return_value = sample_database_orders[2:4]  # AAPL orders
        
        chains = await detector.detect_chains_from_database()
        
        # Should detect AAPL chain using heuristics
        aapl_chains = [c for c in chains if c.chain_symbol == "AAPL"]
        assert len(aapl_chains) == 1
        
        aapl_chain = aapl_chains[0]
        assert aapl_chain.strategy_code is None
        assert aapl_chain.total_orders == 2
        assert aapl_chain.net_premium == Decimal("250.0")  # 750 - 500
        assert aapl_chain.detection_method == "heuristic"
        
    @pytest.mark.asyncio
    async def test_multi_leg_roll_detection(self, detector, sample_database_orders):
        """Test detection of multi-leg roll orders."""
        # Mock database query to return roll order
        detector.options_service.get_orders_for_chain_detection.return_value = [sample_database_orders[4]]  # TSLA roll
        
        chains = await detector.detect_chains_from_database()
        
        # Should detect TSLA roll chain
        tsla_chains = [c for c in chains if c.chain_symbol == "TSLA"]
        assert len(tsla_chains) == 1
        
        tsla_chain = tsla_chains[0]
        assert tsla_chain.total_orders == 1
        assert tsla_chain.net_premium == Decimal("200.0")
        assert tsla_chain.detection_method == "form_source"  # strategy_roll
        
    @pytest.mark.asyncio
    async def test_database_api_fallback(self, detector, legacy_file_orders):
        """Test fallback to API when database is empty."""
        # Mock empty database
        detector.options_service.get_orders_for_chain_detection.return_value = []
        
        # Mock API service to return legacy orders
        with patch.object(detector, '_get_orders_from_api', return_value=legacy_file_orders):
            chains = await detector.detect_chains_from_database()
            
        # Should detect chain from API fallback
        assert len(chains) == 1
        chain = chains[0]
        assert chain.chain_symbol == "AAPL"
        assert chain.total_orders == 2
        assert chain.detection_method == "heuristic"
        
    @pytest.mark.asyncio
    async def test_mixed_detection_methods(self, detector, sample_database_orders):
        """Test that all detection methods work together."""
        # Mock database query to return all sample orders
        detector.options_service.get_orders_for_chain_detection.return_value = sample_database_orders
        
        chains = await detector.detect_chains_from_database()
        
        # Should detect 3 chains with different methods
        assert len(chains) == 3
        
        detection_methods = {c.chain_symbol: c.detection_method for c in chains}
        assert detection_methods["NVDA"] == "strategy_code"
        assert detection_methods["AAPL"] == "heuristic"
        assert detection_methods["TSLA"] == "form_source"
        
    @pytest.mark.asyncio
    async def test_filled_orders_only(self, detector, sample_database_orders):
        """Test that only filled orders are included in chain detection."""
        # Add cancelled order
        cancelled_order = sample_database_orders[0].__class__(
            **{**sample_database_orders[0].__dict__, "state": "cancelled", "order_id": "cancelled-order"}
        )
        
        all_orders = sample_database_orders + [cancelled_order]
        detector.options_service.get_orders_for_chain_detection.return_value = all_orders
        
        chains = await detector.detect_chains_from_database()
        
        # Cancelled order should not affect chain detection
        nvda_chains = [c for c in chains if c.chain_symbol == "NVDA"]
        assert len(nvda_chains) == 1
        assert nvda_chains[0].total_orders == 2  # Only filled orders
        
    @pytest.mark.asyncio
    async def test_chain_financial_calculations(self, detector, sample_database_orders):
        """Test accurate financial calculations for chains."""
        detector.options_service.get_orders_for_chain_detection.return_value = sample_database_orders[:2]  # NVDA
        
        chains = await detector.detect_chains_from_database()
        nvda_chain = [c for c in chains if c.chain_symbol == "NVDA"][0]
        
        # Verify financial calculations
        assert nvda_chain.total_premium_paid == Decimal("6310.0")  # debit order
        assert nvda_chain.total_premium_received == Decimal("13050.0")  # credit order  
        assert nvda_chain.net_premium == Decimal("6740.0")  # profit
        assert nvda_chain.total_quantity == Decimal("2.0")
        
    @pytest.mark.asyncio
    async def test_user_isolation(self, detector, sample_database_orders):
        """Test that chains are properly isolated by user."""
        user1_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        user2_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
        
        # Create orders for different users with same strategy code
        user1_order = sample_database_orders[0].__class__(
            **{**sample_database_orders[0].__dict__, "user_id": user1_id, "order_id": "user1-order"}
        )
        user2_order = sample_database_orders[0].__class__(
            **{**sample_database_orders[0].__dict__, "user_id": user2_id, "order_id": "user2-order"}
        )
        
        # Mock service returns orders for specific user
        detector.options_service.get_orders_for_chain_detection.return_value = [user1_order]
        
        chains = await detector.detect_chains_from_database()
        
        # Should only detect chains for the queried user
        assert len(chains) == 1
        assert chains[0].total_orders == 1
        
    @pytest.mark.asyncio
    async def test_performance_optimization(self, detector, sample_database_orders):
        """Test that database queries are optimized."""
        # Large dataset simulation
        large_dataset = sample_database_orders * 100  # 500 orders
        detector.options_service.get_orders_for_chain_detection.return_value = large_dataset
        
        # Should complete without performance issues
        import time
        start_time = time.time()
        chains = await detector.detect_chains_from_database()
        execution_time = time.time() - start_time
        
        # Should complete in reasonable time (less than 1 second for 500 orders)
        assert execution_time < 1.0
        assert len(chains) == 3  # Should still detect the same 3 distinct chains
        
    @pytest.mark.asyncio
    async def test_backwards_compatibility(self, detector, legacy_file_orders):
        """Test that legacy file-based detection still works."""
        # Test with legacy detector method
        with patch.object(detector, '_get_orders_from_api', return_value=legacy_file_orders):
            legacy_chains = await detector.detect_chains_from_files()
            
        # Should work exactly as before
        assert len(legacy_chains) == 1
        assert legacy_chains[0].chain_symbol == "AAPL"
        assert legacy_chains[0].total_orders == 2