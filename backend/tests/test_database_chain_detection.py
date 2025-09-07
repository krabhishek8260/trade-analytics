"""
Database Integration Tests for Rolled Options Chain Detection

This test suite validates that chain detection works correctly when using 
database-sourced orders data instead of file-based loading. Tests ensure:
- Database queries return correct order format
- Chain detection produces identical results
- P&L calculations match stored vs computed values
- User isolation works correctly
- Performance meets requirements
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4, UUID
import json
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.options_order import OptionsOrder
from app.models.user import User
from app.services.options_order_service import OptionsOrderService
from app.services.rolled_options_chain_detector import RolledOptionsChainDetector
from app.services.robinhood_service import RobinhoodService
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete


class TestDatabaseChainDetection:
    """Test chain detection using database-sourced orders"""

    @pytest.fixture
    async def db_session(self):
        """Create a test database session"""
        async for db in get_db():
            yield db
            break

    @pytest.fixture
    def test_user_id(self):
        """Generate a unique test user ID"""
        return str(uuid4())

    @pytest.fixture
    def mock_rh_service(self):
        """Create a mock Robinhood service"""
        return Mock(spec=RobinhoodService)

    @pytest.fixture
    def options_service(self, mock_rh_service):
        """Create OptionsOrderService instance"""
        return OptionsOrderService(mock_rh_service)

    @pytest.fixture
    def chain_detector(self):
        """Create RolledOptionsChainDetector instance"""
        return RolledOptionsChainDetector()

    async def create_test_user(self, db: AsyncSession, user_id: str):
        """Create a test user in the database"""
        from app.models.user import User
        from sqlalchemy.dialects.postgresql import insert
        
        user_record = {
            "id": user_id,
            "full_name": f"Test User {user_id[:8]}",
            "email": f"test-{user_id}@example.com",
            "is_active": True
        }
        
        stmt = insert(User).values(user_record)
        upsert_stmt = stmt.on_conflict_do_nothing(index_elements=["id"])
        await db.execute(upsert_stmt)
        await db.commit()

    async def create_test_order(self, db: AsyncSession, user_id: str, order_data: dict):
        """Create a test order in the database"""
        from sqlalchemy.dialects.postgresql import insert
        
        # Set default values matching the OptionsOrder model structure
        default_order = {
            "user_id": user_id,
            "order_id": f"test_order_{uuid4().hex[:8]}",
            "state": "filled",
            "type": "limit",
            "chain_symbol": "TEST",
            "direction": "credit",
            "processed_quantity": Decimal("1.0"),
            "processed_premium": Decimal("100.0"),
            "premium": Decimal("1.0"),
            "legs_count": 1,
            "option_type": "call",
            "strike_price": Decimal("100.0"),
            "expiration_date": "2025-06-20",
            "side": "sell",
            "position_effect": "open",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "legs_details": [
                {
                    "strike_price": "100.0",
                    "option_type": "call",
                    "expiration_date": "2025-06-20",
                    "side": "sell",
                    "position_effect": "open",
                    "quantity": "1"
                }
            ],
            "raw_data": {"test": True}
        }
        
        # Merge with provided data
        default_order.update(order_data)
        
        stmt = insert(OptionsOrder).values(default_order)
        upsert_stmt = stmt.on_conflict_do_nothing(index_elements=["order_id"])
        await db.execute(upsert_stmt)
        await db.commit()
        
        return default_order

    async def cleanup_test_data(self, db: AsyncSession, user_id: str):
        """Clean up test data after test"""
        # Delete test orders
        await db.execute(
            delete(OptionsOrder).where(OptionsOrder.user_id == user_id)
        )
        # Delete test user
        await db.execute(
            delete(User).where(User.id == user_id)
        )
        await db.commit()

    @pytest.mark.asyncio
    async def test_database_order_loading(self, db_session, test_user_id, options_service):
        """Test that database order loading returns correct format"""
        try:
            # Create test user and orders
            await self.create_test_user(db_session, test_user_id)
            
            # Create a simple single-leg order
            await self.create_test_order(db_session, test_user_id, {
                "order_id": "test_single_leg",
                "chain_symbol": "HOOD",
                "processed_premium": Decimal("150.0"),
                "direction": "credit",
                "position_effect": "open"
            })
            
            # Create a multi-leg roll order
            await self.create_test_order(db_session, test_user_id, {
                "order_id": "test_roll_order",
                "chain_symbol": "HOOD", 
                "processed_premium": Decimal("50.0"),
                "direction": "debit",
                "legs_count": 2,
                "legs_details": [
                    {
                        "strike_price": "100.0",
                        "option_type": "call",
                        "expiration_date": "2025-06-20",
                        "side": "buy",
                        "position_effect": "close",
                        "quantity": "1"
                    },
                    {
                        "strike_price": "110.0",
                        "option_type": "call", 
                        "expiration_date": "2025-07-18",
                        "side": "sell",
                        "position_effect": "open",
                        "quantity": "1"
                    }
                ]
            })
            
            # Test database loading via OptionsOrderService
            result = await options_service.get_user_orders(
                user_id=UUID(test_user_id),
                limit=100,
                symbol="HOOD"
            )
            
            # Verify successful loading
            assert result["success"] is True
            orders = result["data"]
            assert len(orders) == 2
            
            # Verify order format contains required fields for chain detection
            for order in orders:
                assert "order_id" in order
                assert "chain_symbol" in order
                assert "state" in order
                assert "processed_premium" in order
                assert "direction" in order
                assert "legs_details" in order
                assert order["state"] == "filled"  # Only filled orders returned
                
            # Verify financial fields use correct precision
            single_leg_order = next(o for o in orders if o["order_id"] == "test_single_leg")
            assert single_leg_order["processed_premium"] == 150.0
            assert single_leg_order["direction"] == "credit"
            
            roll_order = next(o for o in orders if o["order_id"] == "test_roll_order")
            assert roll_order["processed_premium"] == 50.0
            assert roll_order["direction"] == "debit"
            assert roll_order["legs_count"] == 2
            
        finally:
            await self.cleanup_test_data(db_session, test_user_id)

    @pytest.mark.asyncio
    async def test_chain_detection_with_database_orders(self, db_session, test_user_id, options_service, chain_detector):
        """Test that chain detection works with database-sourced orders"""
        try:
            await self.create_test_user(db_session, test_user_id)
            
            # Create a complete chain: open -> roll -> close
            base_time = datetime.now() - timedelta(days=30)
            
            # Initial opening order
            await self.create_test_order(db_session, test_user_id, {
                "order_id": "chain_open_1",
                "chain_symbol": "HOOD",
                "processed_premium": Decimal("200.0"),
                "direction": "credit",
                "position_effect": "open",
                "side": "sell",
                "strike_price": Decimal("45.0"),
                "created_at": base_time,
                "legs_details": [
                    {
                        "strike_price": "45.0",
                        "option_type": "call",
                        "expiration_date": "2025-05-16", 
                        "side": "sell",
                        "position_effect": "open",
                        "quantity": "1"
                    }
                ]
            })
            
            # Roll order
            await self.create_test_order(db_session, test_user_id, {
                "order_id": "chain_roll_1",
                "chain_symbol": "HOOD",
                "processed_premium": Decimal("75.0"),
                "direction": "debit",
                "legs_count": 2,
                "created_at": base_time + timedelta(days=7),
                "legs_details": [
                    {
                        "strike_price": "45.0",
                        "option_type": "call",
                        "expiration_date": "2025-05-16",
                        "side": "buy",
                        "position_effect": "close",
                        "quantity": "1"
                    },
                    {
                        "strike_price": "50.0",
                        "option_type": "call",
                        "expiration_date": "2025-06-20",
                        "side": "sell", 
                        "position_effect": "open",
                        "quantity": "1"
                    }
                ],
                "raw_data": {"form_source": "strategy_roll"}
            })
            
            # Final closing order
            await self.create_test_order(db_session, test_user_id, {
                "order_id": "chain_close_1",
                "chain_symbol": "HOOD",
                "processed_premium": Decimal("25.0"),
                "direction": "debit",
                "position_effect": "close",
                "side": "buy",
                "strike_price": Decimal("50.0"),
                "created_at": base_time + timedelta(days=14),
                "legs_details": [
                    {
                        "strike_price": "50.0",
                        "option_type": "call",
                        "expiration_date": "2025-06-20",
                        "side": "buy",
                        "position_effect": "close",
                        "quantity": "1"
                    }
                ]
            })
            
            # Load orders from database
            result = await options_service.get_user_orders(
                user_id=UUID(test_user_id),
                limit=100,
                symbol="HOOD"
            )
            
            assert result["success"] is True
            orders = result["data"]
            
            # Convert to format expected by chain detector
            detector_orders = []
            for order in orders:
                detector_order = {
                    "id": order["order_id"],
                    "chain_symbol": order["chain_symbol"],
                    "underlying_symbol": order["chain_symbol"],
                    "state": order["state"],
                    "direction": order["direction"],
                    "processed_premium": order["processed_premium"],
                    "premium": order["premium"],
                    "legs": order["legs_details"],
                    "legs_count": order["legs_count"],
                    "created_at": order["created_at"],
                    "raw_data": order.get("raw_data", {})
                }
                detector_orders.append(detector_order)
            
            # Run chain detection
            detected_chains = chain_detector.detect_chains(detector_orders)
            
            # Verify chain detection found our chain
            assert len(detected_chains) >= 1
            
            # Find the HOOD chain
            hood_chain = None
            for chain in detected_chains:
                if chain and len(chain) > 0:
                    first_order = chain[0]
                    if first_order.get("chain_symbol") == "HOOD":
                        hood_chain = chain
                        break
            
            assert hood_chain is not None, "Should find HOOD chain"
            assert len(hood_chain) == 3, "Chain should have 3 orders"
            
            # Verify chain order sequence
            chain_order_ids = [order.get("id") for order in hood_chain]
            assert "chain_open_1" in chain_order_ids
            assert "chain_roll_1" in chain_order_ids
            assert "chain_close_1" in chain_order_ids
            
            # Test chain analysis
            chain_analysis = chain_detector.get_chain_analysis(hood_chain)
            assert chain_analysis is not None
            
            # Verify financial calculations
            total_credits = 200.0  # Opening credit
            total_debits = 75.0 + 25.0  # Roll debit + closing debit
            expected_net = total_credits - total_debits
            
            assert chain_analysis.get("total_credits_collected") == total_credits
            assert chain_analysis.get("total_debits_paid") == total_debits
            assert chain_analysis.get("net_premium") == expected_net
            
        finally:
            await self.cleanup_test_data(db_session, test_user_id)

    @pytest.mark.asyncio
    async def test_user_isolation(self, db_session, options_service):
        """Test that users only see their own orders"""
        user1_id = str(uuid4())
        user2_id = str(uuid4())
        
        try:
            # Create two test users
            await self.create_test_user(db_session, user1_id)
            await self.create_test_user(db_session, user2_id)
            
            # Create orders for each user
            await self.create_test_order(db_session, user1_id, {
                "order_id": "user1_order",
                "chain_symbol": "AAPL"
            })
            
            await self.create_test_order(db_session, user2_id, {
                "order_id": "user2_order", 
                "chain_symbol": "AAPL"
            })
            
            # Test that each user only sees their orders
            user1_result = await options_service.get_user_orders(
                user_id=UUID(user1_id),
                limit=100
            )
            
            user2_result = await options_service.get_user_orders(
                user_id=UUID(user2_id),
                limit=100
            )
            
            # Verify isolation
            assert user1_result["success"] is True
            assert user2_result["success"] is True
            
            user1_orders = user1_result["data"]
            user2_orders = user2_result["data"]
            
            assert len(user1_orders) == 1
            assert len(user2_orders) == 1
            
            assert user1_orders[0]["order_id"] == "user1_order"
            assert user2_orders[0]["order_id"] == "user2_order"
            
        finally:
            await self.cleanup_test_data(db_session, user1_id)
            await self.cleanup_test_data(db_session, user2_id)

    @pytest.mark.asyncio
    async def test_financial_calculation_precision(self, db_session, test_user_id, options_service, chain_detector):
        """Test that financial calculations maintain precision and consistency"""
        try:
            await self.create_test_user(db_session, test_user_id)
            
            # Create orders with precise decimal values
            await self.create_test_order(db_session, test_user_id, {
                "order_id": "precise_order_1",
                "processed_premium": Decimal("123.45"),
                "direction": "credit",
                "premium": Decimal("1.2345")
            })
            
            await self.create_test_order(db_session, test_user_id, {
                "order_id": "precise_order_2", 
                "processed_premium": Decimal("67.89"),
                "direction": "debit",
                "premium": Decimal("0.6789")
            })
            
            # Load and verify precision
            result = await options_service.get_user_orders(
                user_id=UUID(test_user_id),
                limit=100
            )
            
            orders = result["data"]
            
            # Verify processed_premium maintains 2 decimal precision
            order1 = next(o for o in orders if o["order_id"] == "precise_order_1")
            order2 = next(o for o in orders if o["order_id"] == "precise_order_2")
            
            assert order1["processed_premium"] == 123.45
            assert order2["processed_premium"] == 67.89
            
            # Verify premium maintains 4 decimal precision  
            assert order1["premium"] == 1.2345
            assert order2["premium"] == 0.6789
            
            # Test calculations in chain analysis
            detector_orders = []
            for order in orders:
                detector_order = {
                    "id": order["order_id"],
                    "direction": order["direction"],
                    "processed_premium": order["processed_premium"],
                    "state": order["state"],
                    "legs": order["legs_details"],
                    "created_at": order["created_at"]
                }
                detector_orders.append(detector_order)
            
            chain_analysis = chain_detector.get_chain_analysis(detector_orders)
            
            # Verify calculated totals
            expected_credits = 123.45
            expected_debits = 67.89
            expected_net = expected_credits - expected_debits
            
            assert abs(chain_analysis.get("total_credits_collected", 0) - expected_credits) < 0.01
            assert abs(chain_analysis.get("total_debits_paid", 0) - expected_debits) < 0.01
            assert abs(chain_analysis.get("net_premium", 0) - expected_net) < 0.01
            
        finally:
            await self.cleanup_test_data(db_session, test_user_id)

    @pytest.mark.asyncio
    async def test_filtered_state_handling(self, db_session, test_user_id, options_service):
        """Test that only filled orders are included in chain detection"""
        try:
            await self.create_test_user(db_session, test_user_id)
            
            # Create orders with different states
            states_to_test = ["filled", "cancelled", "rejected", "failed"]
            
            for i, state in enumerate(states_to_test):
                await self.create_test_order(db_session, test_user_id, {
                    "order_id": f"order_{state}_{i}",
                    "state": state
                })
            
            # Load orders - should only get filled orders
            result = await options_service.get_user_orders(
                user_id=UUID(test_user_id),
                limit=100
            )
            
            orders = result["data"]
            
            # Should only have filled orders
            assert len(orders) == 1
            assert orders[0]["state"] == "filled"
            assert orders[0]["order_id"] == "order_filled_0"
            
        finally:
            await self.cleanup_test_data(db_session, test_user_id)

    @pytest.mark.asyncio
    async def test_performance_with_large_dataset(self, db_session, test_user_id, options_service):
        """Test database query performance with realistic dataset size"""
        try:
            await self.create_test_user(db_session, test_user_id)
            
            # Create realistic number of orders (500+)
            import time
            start_creation = time.time()
            
            symbols = ["AAPL", "TSLA", "HOOD", "NVDA", "MSFT"]
            
            for i in range(100):  # Create 100 orders for performance test
                symbol = symbols[i % len(symbols)]
                await self.create_test_order(db_session, test_user_id, {
                    "order_id": f"perf_order_{i}",
                    "chain_symbol": symbol,
                    "created_at": datetime.now() - timedelta(days=i % 30)
                })
            
            creation_time = time.time() - start_creation
            print(f"Created 100 orders in {creation_time:.2f}s")
            
            # Test query performance
            start_query = time.time()
            
            result = await options_service.get_user_orders(
                user_id=UUID(test_user_id),
                limit=1000,
                page=1
            )
            
            query_time = time.time() - start_query
            print(f"Queried orders in {query_time:.2f}s")
            
            # Performance assertions
            assert query_time < 1.0, f"Query took {query_time:.2f}s, should be under 1s"
            assert result["success"] is True
            assert len(result["data"]) == 100
            
            # Test pagination performance
            start_page = time.time()
            
            page_result = await options_service.get_user_orders(
                user_id=UUID(test_user_id),
                limit=25,
                page=2
            )
            
            page_time = time.time() - start_page
            print(f"Paginated query took {page_time:.2f}s")
            
            assert page_time < 0.5, f"Paginated query took {page_time:.2f}s, should be under 0.5s"
            assert page_result["success"] is True
            assert len(page_result["data"]) == 25
            
        finally:
            await self.cleanup_test_data(db_session, test_user_id)

    @pytest.mark.asyncio
    async def test_jsonb_legs_details_queries(self, db_session, test_user_id, options_service):
        """Test JSONB legs_details field queries and structure"""
        try:
            await self.create_test_user(db_session, test_user_id)
            
            # Create order with complex multi-leg structure
            complex_legs = [
                {
                    "strike_price": "100.0",
                    "option_type": "call",
                    "expiration_date": "2025-06-20",
                    "side": "buy",
                    "position_effect": "close",
                    "quantity": "2"
                },
                {
                    "strike_price": "105.0", 
                    "option_type": "call",
                    "expiration_date": "2025-07-18",
                    "side": "sell",
                    "position_effect": "open",
                    "quantity": "2"
                }
            ]
            
            await self.create_test_order(db_session, test_user_id, {
                "order_id": "complex_multi_leg",
                "legs_count": 2,
                "legs_details": complex_legs
            })
            
            # Load and verify JSONB structure preserved
            result = await options_service.get_user_orders(
                user_id=UUID(test_user_id),
                limit=100
            )
            
            orders = result["data"]
            order = orders[0]
            
            # Verify JSONB structure
            assert order["legs_count"] == 2
            assert len(order["legs_details"]) == 2
            
            leg1, leg2 = order["legs_details"]
            
            assert leg1["strike_price"] == "100.0"
            assert leg1["position_effect"] == "close"
            assert leg1["quantity"] == "2"
            
            assert leg2["strike_price"] == "105.0"
            assert leg2["position_effect"] == "open"
            assert leg2["quantity"] == "2"
            
        finally:
            await self.cleanup_test_data(db_session, test_user_id)


if __name__ == '__main__':
    # Run with: python -m pytest backend/tests/test_database_chain_detection.py -v
    pytest.main([__file__, '-v', '-s'])