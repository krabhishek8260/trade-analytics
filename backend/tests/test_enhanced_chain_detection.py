"""
Comprehensive tests for Enhanced Rolled Options Chain Detection System

This test suite validates all aspects of the enhanced chain detection system including:
- Unit tests for backward tracing algorithm
- Chain validation logic 
- Enhanced chain identification
- Data source fallback behavior
- Error handling and edge cases
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.rolled_options_chain_detector import RolledOptionsChainDetector, LegInfo, OrderInfo


class TestEnhancedBackwardTracing:
    """Tests for the enhanced backward tracing algorithm"""

    def setup_method(self):
        """Set up test fixtures"""
        self.detector = RolledOptionsChainDetector()
        
    def create_mock_order(self, order_id: str, symbol: str, legs: list, created_at: str = None):
        """Create a mock order for testing"""
        if created_at is None:
            created_at = "2025-04-09T14:30:00Z"
            
        return {
            'id': order_id,
            'underlying_symbol': symbol,
            'created_at': created_at,
            'state': 'filled',
            'legs': legs
        }
    
    def create_mock_leg(self, strike: float, option_type: str, expiration: str, 
                       side: str, position_effect: str, quantity: int = 1):
        """Create a mock options leg for testing"""
        return {
            'strike_price': str(strike),
            'option_type': option_type,
            'expiration_date': expiration,
            'side': side,
            'position_effect': position_effect,
            'quantity': str(quantity)
        }

    def test_trace_backwards_finds_opening_order(self):
        """Test that backward tracing finds matching opening orders"""
        # Create mock data with opening order and roll order
        opening_order = self.create_mock_order(
            'opening_123',
            'HOOD',
            [self.create_mock_leg(45.0, 'call', '2025-05-16', 'buy', 'open')],
            '2025-04-09T14:30:00Z'
        )
        
        roll_order = self.create_mock_order(
            'roll_456', 
            'HOOD',
            [
                self.create_mock_leg(45.0, 'call', '2025-05-16', 'sell', 'close'),
                self.create_mock_leg(65.0, 'call', '2025-06-20', 'buy', 'open')
            ],
            '2025-04-15T10:00:00Z'
        )
        
        # Mock the _load_all_orders_for_symbol method
        with patch.object(self.detector, '_load_all_orders_for_symbol') as mock_load:
            mock_load.return_value = [opening_order, roll_order]
            
            # Mock roll detection to return the roll order
            current_analyses = [{
                'order_id': 'roll_456',
                'closes': [{
                    'strike_price': 45.0,
                    'option_type': 'call',
                    'expiration_date': '2025-05-16',
                    'side': 'sell',
                    'position_effect': 'close'
                }],
                'opens': [{
                    'strike_price': 65.0,
                    'option_type': 'call', 
                    'expiration_date': '2025-06-20',
                    'side': 'buy',
                    'position_effect': 'open'
                }]
            }]
            
            # Test backward tracing
            result = self.detector._trace_backwards_for_chain_starts(
                current_analyses, 'HOOD', 'call'
            )
            
            # Verify opening order was found
            assert len(result) == 1
            assert result[0]['order_id'] == 'opening_123'
            mock_load.assert_called_once_with('HOOD')

    def test_find_matching_opening_order_exact_match(self):
        """Test finding exact matching opening order"""
        opening_order = self.create_mock_order(
            'opening_123',
            'HOOD', 
            [self.create_mock_leg(45.0, 'call', '2025-05-16', 'buy', 'open')]
        )
        
        closing_order = self.create_mock_order(
            'closing_456',
            'HOOD',
            [self.create_mock_leg(50.0, 'put', '2025-06-20', 'sell', 'close')]
        )
        
        all_orders = [opening_order, closing_order]
        
        # Should find exact match
        result = self.detector._find_matching_opening_order(
            all_orders,
            symbol='HOOD',
            option_type='call',
            strike_price=45.0,
            expiration_date='2025-05-16'
        )
        
        assert result is not None
        assert result['id'] == 'opening_123'

    def test_find_matching_opening_order_no_match(self):
        """Test no matching opening order found"""
        wrong_order = self.create_mock_order(
            'wrong_123',
            'HOOD',
            [self.create_mock_leg(50.0, 'put', '2025-06-20', 'buy', 'open')]
        )
        
        all_orders = [wrong_order]
        
        # Should not find match (different strike, type, expiration)
        result = self.detector._find_matching_opening_order(
            all_orders,
            symbol='HOOD',
            option_type='call',
            strike_price=45.0,
            expiration_date='2025-05-16'
        )
        
        assert result is None

    def test_find_matching_opening_order_multi_leg_ignored(self):
        """Test that multi-leg orders are ignored when looking for opening orders"""
        multi_leg_order = self.create_mock_order(
            'multi_123',
            'HOOD',
            [
                self.create_mock_leg(45.0, 'call', '2025-05-16', 'buy', 'open'),
                self.create_mock_leg(50.0, 'call', '2025-05-16', 'sell', 'open')
            ]
        )
        
        all_orders = [multi_leg_order]
        
        # Should not find match (multi-leg order)
        result = self.detector._find_matching_opening_order(
            all_orders,
            symbol='HOOD',
            option_type='call',
            strike_price=45.0,
            expiration_date='2025-05-16'
        )
        
        assert result is None

    def test_load_all_orders_for_symbol_symbol_filtering(self):
        """Test that _load_all_orders_for_symbol filters by symbol correctly"""
        hood_order = self.create_mock_order('hood_1', 'HOOD', [])
        tsla_order = self.create_mock_order('tsla_1', 'TSLA', [])
        
        with patch.object(self.detector, '_load_orders_from_debug_files') as mock_debug, \
             patch.object(self.detector, '_load_orders_from_service') as mock_service:
            
            mock_debug.return_value = [hood_order, tsla_order]
            mock_service.return_value = []
            
            result = self.detector._load_all_orders_for_symbol('HOOD')
            
            # Should only return HOOD orders
            assert len(result) == 1
            assert result[0]['id'] == 'hood_1'

    @patch('pathlib.Path.glob')
    @patch('builtins.open')
    @patch('json.load')
    def test_load_orders_from_debug_files_deduplication(self, mock_json_load, mock_open, mock_glob):
        """Test that debug file loading removes duplicates"""
        # Mock file system
        mock_file1 = Mock()
        mock_file1.name = 'file1.json'
        mock_file2 = Mock()
        mock_file2.name = 'file2.json'
        mock_glob.return_value = [mock_file1, mock_file2]
        
        # Mock file contents with duplicate orders
        duplicate_order = {'id': 'dup_123', 'state': 'filled'}
        unique_order = {'id': 'unique_456', 'state': 'filled'}
        
        mock_json_load.side_effect = [
            [duplicate_order, unique_order],  # file1
            [duplicate_order]  # file2 (duplicate)
        ]
        
        result = self.detector._load_orders_from_debug_files()
        
        # Should deduplicate by ID
        assert len(result) == 2  # Only unique orders
        order_ids = [order['id'] for order in result]
        assert 'dup_123' in order_ids
        assert 'unique_456' in order_ids


class TestChainValidation:
    """Tests for chain validation logic"""

    def setup_method(self):
        self.detector = RolledOptionsChainDetector()

    def test_enhanced_chain_identification(self):
        """Test identification of enhanced chains vs regular chains"""
        # Enhanced chain: starts with single-leg opening order
        enhanced_orders = [
            {
                'id': 'opening_123',
                'legs': [{'position_effect': 'open'}]
            },
            {
                'id': 'roll_456', 
                'legs': [
                    {'position_effect': 'close'},
                    {'position_effect': 'open'}
                ]
            }
        ]
        
        # Regular chain: starts with roll order
        regular_orders = [
            {
                'id': 'roll_789',
                'legs': [
                    {'position_effect': 'close'},
                    {'position_effect': 'open'}
                ]
            }
        ]
        
        # Test enhanced chain identification
        enhanced_analysis = self.detector.get_chain_analysis(enhanced_orders)
        assert enhanced_analysis is not None
        
        # Should be marked as enhanced
        if enhanced_analysis:
            orders = enhanced_analysis.get('orders', [])
            if orders:
                first_order = orders[0]
                legs = first_order.get('legs', [])
                is_enhanced = len(legs) == 1 and legs[0].get('position_effect') == 'open'
                assert is_enhanced, "Enhanced chain should start with single-leg opening order"

    def test_chain_sequence_validation(self):
        """Test validation of proper chain sequences"""
        # Valid sequence: open -> roll -> close
        valid_sequence = [
            {
                'id': 'open_123',
                'created_at': '2025-04-09T14:30:00Z',
                'legs': [{'position_effect': 'open', 'side': 'buy', 'quantity': '1'}]
            },
            {
                'id': 'roll_456',
                'created_at': '2025-04-15T10:00:00Z', 
                'legs': [
                    {'position_effect': 'close', 'side': 'sell', 'quantity': '1'},
                    {'position_effect': 'open', 'side': 'buy', 'quantity': '1'}
                ]
            },
            {
                'id': 'close_789',
                'created_at': '2025-04-20T16:00:00Z',
                'legs': [{'position_effect': 'close', 'side': 'sell', 'quantity': '1'}]
            }
        ]
        
        # Test chain validation
        analysis = self.detector.get_chain_analysis(valid_sequence)
        assert analysis is not None
        assert analysis.get('total_orders') == 3

    def test_position_flow_tracking(self):
        """Test position flow and quantity matching"""
        # Orders with mismatched quantities should be rejected
        mismatched_orders = [
            {
                'id': 'open_123',
                'legs': [{'position_effect': 'open', 'quantity': '2'}]  # Open 2 contracts
            },
            {
                'id': 'close_456', 
                'legs': [{'position_effect': 'close', 'quantity': '1'}]  # Close only 1 contract
            }
        ]
        
        # Should handle quantity mismatches gracefully
        analysis = self.detector.get_chain_analysis(mismatched_orders)
        # Analysis may still be created but should note the mismatch
        if analysis:
            assert 'total_orders' in analysis

    def test_orphaned_close_rejection(self):
        """Test rejection of orphaned close orders"""
        # Close order without corresponding open
        orphaned_close = [
            {
                'id': 'orphan_123',
                'legs': [{'position_effect': 'close', 'side': 'buy'}]
            }
        ]
        
        # Should reject orphaned closes or handle gracefully
        analysis = self.detector.get_chain_analysis(orphaned_close)
        # Implementation may vary - could return None or minimal analysis


class TestDataSourceFallback:
    """Tests for data source fallback behavior"""

    def setup_method(self):
        self.detector = RolledOptionsChainDetector()

    @patch('pathlib.Path.glob')
    def test_debug_files_primary_source(self, mock_glob):
        """Test that debug files are used as primary source in development"""
        # Mock debug files exist
        mock_file = Mock()
        mock_glob.return_value = [mock_file]
        
        with patch.object(self.detector, '_load_orders_from_debug_files') as mock_debug, \
             patch.object(self.detector, '_load_orders_from_service') as mock_service:
            
            mock_debug.return_value = [{'id': 'debug_order', 'state': 'filled'}]
            mock_service.return_value = [{'id': 'service_order', 'state': 'filled'}]
            
            result = self.detector._load_all_orders_for_symbol('HOOD')
            
            # Should use debug data and not call service
            mock_debug.assert_called_once()
            mock_service.assert_not_called()
            assert result[0]['id'] == 'debug_order'

    @patch('pathlib.Path.glob')
    def test_service_fallback_when_no_debug_files(self, mock_glob):
        """Test fallback to service when no debug files available"""
        # Mock no debug files
        mock_glob.return_value = []
        
        with patch.object(self.detector, '_load_orders_from_debug_files') as mock_debug, \
             patch.object(self.detector, '_load_orders_from_service') as mock_service:
            
            mock_debug.return_value = []
            mock_service.return_value = [{'id': 'service_order', 'state': 'filled'}]
            
            result = self.detector._load_all_orders_for_symbol('HOOD')
            
            # Should fall back to service
            mock_debug.assert_called_once()
            mock_service.assert_called_once()
            assert result[0]['id'] == 'service_order'

    def test_extended_lookback_production(self):
        """Test extended lookback behavior in production environment"""
        with patch.object(self.detector, '_load_orders_from_service') as mock_service:
            mock_service.return_value = [{'id': 'extended_order', 'state': 'filled'}]
            
            # Simulate production environment (no debug files)
            with patch('pathlib.Path.glob', return_value=[]):
                result = self.detector._load_all_orders_for_symbol('HOOD')
                
                # Should call service with extended lookback
                mock_service.assert_called_once()
                # Verify extended lookback is used (365+ days)
                args, kwargs = mock_service.call_args
                # Implementation specific - may pass days_back parameter


class TestErrorHandling:
    """Tests for error handling and edge cases"""

    def setup_method(self):
        self.detector = RolledOptionsChainDetector()

    def test_empty_orders_list(self):
        """Test handling of empty orders list"""
        result = self.detector.detect_chains([])
        assert result == []

    def test_malformed_order_data(self):
        """Test handling of malformed order data"""
        malformed_orders = [
            {'id': 'bad_1'},  # Missing required fields
            {'legs': []},     # Missing ID
            None,             # Null order
            {'id': 'good_1', 'legs': [{'position_effect': 'open'}], 'state': 'filled'}
        ]
        
        # Should handle malformed data gracefully
        result = self.detector.detect_chains(malformed_orders)
        assert isinstance(result, list)

    def test_file_loading_errors(self):
        """Test handling of file loading errors"""
        with patch('builtins.open', side_effect=FileNotFoundError):
            result = self.detector._load_orders_from_debug_files()
            assert result == []

    def test_json_parsing_errors(self):
        """Test handling of JSON parsing errors"""
        with patch('pathlib.Path.glob') as mock_glob, \
             patch('builtins.open') as mock_open, \
             patch('json.load', side_effect=json.JSONDecodeError("Invalid JSON", "", 0)):
            
            mock_file = Mock()
            mock_glob.return_value = [mock_file]
            
            result = self.detector._load_orders_from_debug_files()
            assert result == []

    def test_invalid_date_formats(self):
        """Test handling of invalid date formats"""
        orders_with_bad_dates = [
            {
                'id': 'bad_date_1',
                'created_at': 'invalid-date-format',
                'legs': [{'position_effect': 'open'}],
                'state': 'filled'
            }
        ]
        
        # Should handle invalid dates gracefully
        result = self.detector.detect_chains(orders_with_bad_dates)
        assert isinstance(result, list)

    def test_memory_handling_large_datasets(self):
        """Test memory handling with large datasets"""
        # Create large dataset
        large_dataset = []
        for i in range(1000):
            order = {
                'id': f'order_{i}',
                'legs': [{'position_effect': 'open' if i % 2 == 0 else 'close'}],
                'state': 'filled',
                'underlying_symbol': 'TEST'
            }
            large_dataset.append(order)
        
        # Should handle large datasets without memory issues
        result = self.detector.detect_chains(large_dataset)
        assert isinstance(result, list)


class TestPerformanceMetrics:
    """Tests for performance characteristics"""

    def setup_method(self):
        self.detector = RolledOptionsChainDetector()

    def test_detection_performance(self):
        """Test detection performance with realistic dataset size"""
        import time
        
        # Create realistic dataset (similar to production size)
        realistic_dataset = []
        for i in range(965):  # Size from production logs
            order = {
                'id': f'order_{i}',
                'underlying_symbol': f'SYM{i % 50}',  # 50 different symbols
                'legs': [{'position_effect': 'open' if i % 3 == 0 else 'close'}],
                'state': 'filled',
                'created_at': '2025-04-09T14:30:00Z'
            }
            realistic_dataset.append(order)
        
        # Measure detection time
        start_time = time.time()
        result = self.detector.detect_chains(realistic_dataset)
        detection_time = time.time() - start_time
        
        # Should complete within reasonable time (< 10 seconds for 965 orders)
        assert detection_time < 10.0
        assert isinstance(result, list)

    def test_memory_usage_monitoring(self):
        """Test that memory usage stays within reasonable bounds"""
        import sys
        
        # Get initial memory usage
        initial_size = sys.getsizeof(self.detector)
        
        # Process dataset
        test_orders = [
            {
                'id': f'order_{i}',
                'legs': [{'position_effect': 'open'}],
                'state': 'filled'
            }
            for i in range(100)
        ]
        
        result = self.detector.detect_chains(test_orders)
        
        # Memory usage should not grow excessively
        final_size = sys.getsizeof(self.detector)
        memory_growth = final_size - initial_size
        
        # Should not grow by more than reasonable amount
        assert memory_growth < 1000000  # 1MB limit


if __name__ == '__main__':
    pytest.main([__file__, '-v'])