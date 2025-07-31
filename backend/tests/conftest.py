"""
Pytest configuration and fixtures for Enhanced Chain Detection tests

This file provides common fixtures and configuration for all test suites
in the enhanced chain detection system.
"""

import pytest
import asyncio
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock
import sys

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.rolled_options_chain_detector import RolledOptionsChainDetector
from app.services.rolled_options_cron_service import RolledOptionsCronService


@pytest.fixture
def detector():
    """Provide a fresh RolledOptionsChainDetector instance for each test"""
    return RolledOptionsChainDetector()


@pytest.fixture
def cron_service():
    """Provide a fresh RolledOptionsCronService instance for each test"""
    return RolledOptionsCronService()


@pytest.fixture
def sample_opening_order():
    """Provide a sample single-leg opening order"""
    return {
        'id': 'opening_123',
        'underlying_symbol': 'HOOD',
        'created_at': '2025-04-09T14:30:00Z',
        'state': 'filled',
        'legs': [{
            'strike_price': '45.0',
            'option_type': 'call',
            'expiration_date': '2025-05-16',
            'side': 'buy',
            'position_effect': 'open',
            'quantity': '1'
        }]
    }


@pytest.fixture
def sample_roll_order():
    """Provide a sample roll order (multi-leg with close+open)"""
    return {
        'id': 'roll_456',
        'underlying_symbol': 'HOOD',
        'created_at': '2025-04-15T10:00:00Z',
        'state': 'filled',
        'legs': [
            {
                'strike_price': '45.0',
                'option_type': 'call',
                'expiration_date': '2025-05-16',
                'side': 'sell',
                'position_effect': 'close',
                'quantity': '1'
            },
            {
                'strike_price': '65.0',
                'option_type': 'call',
                'expiration_date': '2025-06-20',
                'side': 'buy',
                'position_effect': 'open',
                'quantity': '1'
            }
        ]
    }


@pytest.fixture
def sample_closing_order():
    """Provide a sample single-leg closing order"""
    return {
        'id': 'closing_789',
        'underlying_symbol': 'HOOD',
        'created_at': '2025-04-20T16:00:00Z',
        'state': 'filled',
        'legs': [{
            'strike_price': '65.0',
            'option_type': 'call',
            'expiration_date': '2025-06-20',
            'side': 'sell',
            'position_effect': 'close',
            'quantity': '1'
        }]
    }


@pytest.fixture
def enhanced_chain_sequence(sample_opening_order, sample_roll_order, sample_closing_order):
    """Provide a complete enhanced chain sequence (opening -> roll -> closing)"""
    return [sample_opening_order, sample_roll_order, sample_closing_order]


@pytest.fixture
def regular_chain_sequence(sample_roll_order, sample_closing_order):
    """Provide a regular chain sequence (starts with roll order)"""
    return [sample_roll_order, sample_closing_order]


@pytest.fixture
def large_dataset():
    """Provide a large dataset for performance testing"""
    orders = []
    symbols = ['AAPL', 'TSLA', 'MSFT', 'GOOGL', 'AMZN']
    
    for i in range(1000):
        symbol = symbols[i % len(symbols)]
        strike = 100.0 + (i % 20) * 5.0
        
        order = {
            'id': f'large_order_{i}',
            'underlying_symbol': symbol,
            'created_at': f'2025-04-{(i % 30) + 1:02d}T{(i % 24):02d}:30:00Z',
            'state': 'filled',
            'legs': [{
                'strike_price': str(strike),
                'option_type': 'call' if i % 2 == 0 else 'put',
                'expiration_date': '2025-06-20',
                'side': 'buy' if i % 3 == 0 else 'sell',
                'position_effect': 'open' if i % 4 == 0 else 'close',
                'quantity': '1'
            }]
        }
        orders.append(order)
    
    return orders


@pytest.fixture
def mock_database_session():
    """Provide a mock database session for testing"""
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    mock_db.begin_nested = AsyncMock()
    
    # Mock nested transaction
    mock_nested = AsyncMock()
    mock_nested.__aenter__ = AsyncMock(return_value=mock_nested)
    mock_nested.__aexit__ = AsyncMock(return_value=None)
    mock_nested.commit = AsyncMock()
    mock_nested.rollback = AsyncMock()
    mock_db.begin_nested.return_value = mock_nested
    
    return mock_db


@pytest.fixture
def mock_debug_files():
    """Provide mock debug files for testing"""
    sample_orders = [
        {
            'id': 'debug_order_1',
            'underlying_symbol': 'DEBUG',
            'state': 'filled',
            'legs': [{'position_effect': 'open'}]
        },
        {
            'id': 'debug_order_2', 
            'underlying_symbol': 'DEBUG',
            'state': 'filled',
            'legs': [{'position_effect': 'close'}]
        }
    ]
    
    # Create temporary files
    with tempfile.NamedTemporaryFile(mode='w', suffix='_options_orders_debug.json', delete=False) as temp_file:
        json.dump(sample_orders, temp_file)
        temp_file.flush()
        
        temp_path = Path(temp_file.name)
        
        yield temp_path
        
        # Clean up
        temp_path.unlink()


@pytest.fixture
def corrupted_orders():
    """Provide various types of corrupted order data for testing"""
    return [
        None,  # Null order
        {},  # Empty order
        {'id': 'missing_fields'},  # Missing required fields
        {'legs': 'not_a_list'},  # Wrong data type
        {'id': 'bad_date', 'created_at': 'invalid-date', 'legs': [], 'state': 'filled'},
        {'id': 'bad_legs', 'legs': [None, 'not_a_dict'], 'state': 'filled'},
        {  # Valid order for comparison
            'id': 'valid_order',
            'legs': [{'position_effect': 'open'}],
            'state': 'filled',
            'created_at': '2025-04-09T14:30:00Z'
        }
    ]


@pytest.fixture
def test_user_info():
    """Provide test user information for processing tests"""
    return {
        'user_id': 'test_user_123',
        'last_processed_at': None,
        'processing_status': 'pending',
        'full_sync_required': True
    }


@pytest.fixture
def sample_chain_analysis():
    """Provide sample chain analysis data for database tests"""
    return {
        'chain_id': 'test_chain_456',
        'underlying_symbol': 'TEST',
        'status': 'active',
        'initial_strategy': 'long_call',
        'start_date': '2025-04-09T14:30:00Z',
        'last_activity_date': '2025-04-20T16:00:00Z',
        'total_orders': 3,
        'roll_count': 1,
        'total_credits_collected': 0.0,
        'total_debits_paid': 500.0,
        'net_premium': -500.0,
        'total_pnl': 150.0,
        'orders': [],
        'latest_position': {
            'symbol': 'TEST',
            'option_type': 'call',
            'strike_price': 65.0,
            'expiration_date': '2025-06-20',
            'quantity': 1
        }
    }


@pytest.fixture(scope='session')
def event_loop():
    """Create an event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Pytest configuration
def pytest_configure(config):
    """Configure pytest settings"""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically"""
    for item in items:
        # Mark async tests
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)
        
        # Mark performance tests
        if 'performance' in item.nodeid.lower():
            item.add_marker(pytest.mark.performance)
        
        # Mark integration tests
        if 'integration' in item.nodeid.lower():
            item.add_marker(pytest.mark.integration)
        
        # Mark slow tests
        if any(keyword in item.nodeid.lower() for keyword in ['large_dataset', 'concurrent', 'memory']):
            item.add_marker(pytest.mark.slow)


# Helper functions for tests
def create_mock_order(order_id: str, symbol: str, legs: list, created_at: str = None):
    """Helper function to create mock orders"""
    if created_at is None:
        created_at = '2025-04-09T14:30:00Z'
    
    return {
        'id': order_id,
        'underlying_symbol': symbol,
        'created_at': created_at,
        'state': 'filled',
        'legs': legs
    }


def create_mock_leg(strike: float, option_type: str, expiration: str, 
                   side: str, position_effect: str, quantity: int = 1):
    """Helper function to create mock option legs"""
    return {
        'strike_price': str(strike),
        'option_type': option_type,
        'expiration_date': expiration,
        'side': side,
        'position_effect': position_effect,
        'quantity': str(quantity)
    }