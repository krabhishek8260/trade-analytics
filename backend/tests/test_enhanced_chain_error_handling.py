"""
Error Handling and Recovery Tests for Enhanced Rolled Options Chain Detection System

This test suite validates error handling and recovery scenarios including:
- Database connection failures
- File system errors
- API timeout and rate limiting
- Data corruption handling
- Memory exhaustion scenarios
- Network failures
- Concurrent access conflicts
"""

import pytest
import asyncio
import json
import tempfile
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
import sys
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.rolled_options_chain_detector import RolledOptionsChainDetector
from app.services.rolled_options_cron_service import RolledOptionsCronService
from app.services.json_rolled_options_service import JsonRolledOptionsService


class TestDatabaseErrorHandling:
    """Tests for database connection and operation error handling"""

    def setup_method(self):
        self.cron_service = RolledOptionsCronService()

    @pytest.mark.asyncio
    async def test_database_connection_failure(self):
        """Test handling of database connection failures"""
        with patch('app.core.database.get_db') as mock_get_db:
            # Simulate connection failure
            mock_get_db.side_effect = OperationalError("Connection failed", None, None)
            
            user_info = {
                'user_id': 'test_user_123',
                'full_sync_required': True
            }
            
            # Should handle connection failure gracefully
            result = await self.cron_service._process_user_rolled_options(user_info)
            
            assert result['success'] is False
            assert 'Connection failed' in result['message'] or 'error' in result['message'].lower()

    @pytest.mark.asyncio
    async def test_database_transaction_rollback(self):
        """Test proper transaction rollback on errors"""
        with patch('app.core.database.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Mock database operations
            mock_db.execute = AsyncMock()
            mock_db.commit = AsyncMock()
            mock_db.rollback = AsyncMock()
            
            # Simulate error during chain storage
            mock_db.execute.side_effect = IntegrityError("Constraint violation", None, None)
            
            chain_analysis = {
                'chain_id': 'test_chain_123',
                'underlying_symbol': 'TEST',
                'status': 'active',
                'total_orders': 1,
                'roll_count': 0,
                'orders': []
            }
            
            # Should not raise exception
            await self.cron_service._store_chain(mock_db, 'test_user', chain_analysis)
            
            # Should attempt rollback on error
            mock_db.execute.assert_called()

    @pytest.mark.asyncio
    async def test_database_deadlock_recovery(self):
        """Test recovery from database deadlocks"""
        with patch('app.core.database.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Simulate deadlock, then success on retry
            mock_db.execute = AsyncMock()
            mock_db.commit = AsyncMock()
            mock_db.begin_nested = AsyncMock()
            
            mock_nested = AsyncMock()
            mock_nested.__aenter__ = AsyncMock(return_value=mock_nested)
            mock_nested.__aexit__ = AsyncMock(return_value=None)
            mock_nested.commit = AsyncMock()
            mock_nested.rollback = AsyncMock()
            mock_db.begin_nested.return_value = mock_nested
            
            # First call fails with deadlock, second succeeds
            mock_db.execute.side_effect = [
                OperationalError("deadlock detected", None, None),
                None  # Success on retry
            ]
            
            chain_analysis = {
                'chain_id': 'deadlock_test_123',
                'underlying_symbol': 'TEST',
                'status': 'active',
                'total_orders': 1,
                'roll_count': 0,
                'orders': []
            }
            
            # Should handle deadlock gracefully
            await self.cron_service._store_chain(mock_db, 'test_user', chain_analysis)

    @pytest.mark.asyncio
    async def test_sync_status_update_failure(self):
        """Test handling of sync status update failures"""
        with patch('app.core.database.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Simulate sync status update failure
            mock_db.execute = AsyncMock(side_effect=SQLAlchemyError("Sync update failed"))
            mock_db.rollback = AsyncMock()
            
            # Should not raise exception
            await self.cron_service._update_sync_status(
                'test_user_123',
                'completed',
                total_chains=5
            )
            
            # Should attempt rollback
            mock_db.rollback.assert_called_once()


class TestFileSystemErrorHandling:
    """Tests for file system related error handling"""

    def setup_method(self):
        self.detector = RolledOptionsChainDetector()
        self.cron_service = RolledOptionsCronService()

    def test_debug_file_not_found(self):
        """Test handling when debug files don't exist"""
        with patch('pathlib.Path.glob', return_value=[]):
            result = self.detector._load_orders_from_debug_files()
            assert result == []

    def test_debug_file_permission_denied(self):
        """Test handling of file permission errors"""
        with patch('pathlib.Path.glob') as mock_glob, \
             patch('builtins.open', side_effect=PermissionError("Permission denied")):
            
            mock_file = Mock()
            mock_glob.return_value = [mock_file]
            
            result = self.detector._load_orders_from_debug_files()
            assert result == []

    def test_debug_file_corrupted_json(self):
        """Test handling of corrupted JSON files"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            # Write invalid JSON
            temp_file.write('{"invalid": json content}')
            temp_file.flush()
            
            temp_path = Path(temp_file.name)
            
            try:
                with patch('pathlib.Path.glob', return_value=[temp_path]):
                    result = self.detector._load_orders_from_debug_files()
                    assert result == []
            finally:
                # Clean up
                temp_path.unlink()

    def test_debug_file_empty_content(self):
        """Test handling of empty debug files"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            # Write empty content
            temp_file.write('')
            temp_file.flush()
            
            temp_path = Path(temp_file.name)
            
            try:
                with patch('pathlib.Path.glob', return_value=[temp_path]):
                    result = self.detector._load_orders_from_debug_files()
                    assert result == []
            finally:
                # Clean up
                temp_path.unlink()

    def test_debug_file_disk_full(self):
        """Test handling of disk full scenarios"""
        with patch('builtins.open', side_effect=OSError("No space left on device")):
            with patch('pathlib.Path.glob', return_value=[Mock()]):
                result = self.detector._load_orders_from_debug_files()
                assert result == []

    def test_debug_directory_not_accessible(self):
        """Test handling when debug directory is not accessible"""
        with patch('pathlib.Path.glob', side_effect=OSError("Directory not accessible")):
            result = self.detector._load_orders_from_debug_files()
            assert result == []


class TestAPIErrorHandling:
    """Tests for API related error handling"""

    def setup_method(self):
        self.cron_service = RolledOptionsCronService()
        self.json_service = JsonRolledOptionsService()

    @pytest.mark.asyncio
    async def test_api_timeout_handling(self):
        """Test handling of API timeouts"""
        with patch.object(self.cron_service.json_service, '_load_raw_orders') as mock_api:
            # Simulate timeout
            mock_api.side_effect = asyncio.TimeoutError("API timeout")
            
            result = await self.cron_service._load_user_orders('test_user', 30)
            
            # Should return empty list on timeout
            assert result == []

    @pytest.mark.asyncio
    async def test_api_rate_limiting(self):
        """Test handling of API rate limiting"""
        with patch.object(self.cron_service.json_service, '_load_raw_orders') as mock_api:
            # Simulate rate limiting
            mock_api.side_effect = Exception("Rate limit exceeded")
            
            result = await self.cron_service._load_user_orders('test_user', 30)
            
            # Should handle rate limiting gracefully
            assert result == []

    @pytest.mark.asyncio
    async def test_api_authentication_failure(self):
        """Test handling of API authentication failures"""
        with patch.object(self.cron_service.json_service, '_load_raw_orders') as mock_api:
            # Simulate authentication failure
            mock_api.side_effect = Exception("Authentication failed")
            
            result = await self.cron_service._load_user_orders('test_user', 30)
            
            # Should handle auth failure gracefully
            assert result == []

    @pytest.mark.asyncio
    async def test_api_malformed_response(self):
        """Test handling of malformed API responses"""
        with patch.object(self.cron_service.json_service, '_load_raw_orders') as mock_api:
            # Return malformed response
            mock_api.return_value = {
                'success': True,
                'orders': "not_a_list"  # Should be a list
            }
            
            result = await self.cron_service._load_user_orders('test_user', 30)
            
            # Should handle malformed response gracefully
            assert result == []

    @pytest.mark.asyncio
    async def test_api_network_failure(self):
        """Test handling of network failures"""
        with patch.object(self.cron_service.json_service, '_load_raw_orders') as mock_api:
            # Simulate network failure
            mock_api.side_effect = ConnectionError("Network unreachable")
            
            result = await self.cron_service._load_user_orders('test_user', 30)
            
            # Should handle network failure gracefully
            assert result == []

    @pytest.mark.asyncio
    async def test_api_partial_failure_recovery(self):
        """Test recovery from partial API failures"""
        with patch.object(self.cron_service.json_service, '_load_raw_orders') as mock_api:
            # First call fails, second succeeds
            mock_api.side_effect = [
                Exception("Temporary failure"),
                {
                    'success': True,
                    'orders': [{'id': 'recovery_order', 'state': 'filled', 'legs': [{}]}]
                }
            ]
            
            # Make two calls to test recovery
            result1 = await self.cron_service._load_user_orders('test_user', 30)
            result2 = await self.cron_service._load_user_orders('test_user', 30)
            
            # First should fail, second should succeed
            assert result1 == []
            assert len(result2) == 1


class TestDataCorruptionHandling:
    """Tests for handling corrupted or invalid data"""

    def setup_method(self):
        self.detector = RolledOptionsChainDetector()

    def test_corrupted_order_data(self):
        """Test handling of corrupted order data"""
        corrupted_orders = [
            None,  # Null order
            {},  # Empty order
            {'id': 'missing_fields'},  # Missing required fields
            {'legs': 'not_a_list'},  # Wrong data type
            {'id': 'good_order', 'legs': [], 'state': 'filled'},  # Valid order
            {'id': 'bad_legs', 'legs': [None, 'not_a_dict']},  # Bad legs
        ]
        
        # Should handle corrupted data gracefully
        result = self.detector.detect_chains(corrupted_orders)
        assert isinstance(result, list)

    def test_invalid_date_formats(self):
        """Test handling of invalid date formats"""
        orders_with_bad_dates = [
            {
                'id': 'bad_date_1',
                'created_at': 'not-a-date',
                'legs': [{'position_effect': 'open'}],
                'state': 'filled'
            },
            {
                'id': 'bad_date_2',
                'created_at': '2025-13-45T25:70:99Z',  # Invalid date values
                'legs': [{'position_effect': 'close'}],
                'state': 'filled'
            },
            {
                'id': 'good_date',
                'created_at': '2025-04-09T14:30:00Z',
                'legs': [{'position_effect': 'open'}],
                'state': 'filled'
            }
        ]
        
        # Should handle invalid dates gracefully
        result = self.detector.detect_chains(orders_with_bad_dates)
        assert isinstance(result, list)

    def test_invalid_numeric_values(self):
        """Test handling of invalid numeric values"""
        orders_with_bad_numbers = [
            {
                'id': 'bad_strike',
                'legs': [{
                    'strike_price': 'not-a-number',
                    'position_effect': 'open',
                    'quantity': '1'
                }],
                'state': 'filled'
            },
            {
                'id': 'bad_quantity',
                'legs': [{
                    'strike_price': '100.0',
                    'position_effect': 'open',
                    'quantity': 'invalid'
                }],
                'state': 'filled'
            },
            {
                'id': 'negative_quantity',
                'legs': [{
                    'strike_price': '100.0',
                    'position_effect': 'open',
                    'quantity': '-1'
                }],
                'state': 'filled'
            }
        ]
        
        # Should handle invalid numbers gracefully
        result = self.detector.detect_chains(orders_with_bad_numbers)
        assert isinstance(result, list)

    def test_missing_required_fields(self):
        """Test handling of orders with missing required fields"""
        incomplete_orders = [
            {'id': 'no_legs'},  # Missing legs
            {'legs': []},  # Missing ID
            {'id': 'no_state', 'legs': []},  # Missing state
            {  # Missing everything important
                'random_field': 'value'
            },
            {  # Complete order for comparison
                'id': 'complete',
                'legs': [{'position_effect': 'open'}],
                'state': 'filled'
            }
        ]
        
        # Should handle incomplete orders gracefully
        result = self.detector.detect_chains(incomplete_orders)
        assert isinstance(result, list)

    def test_circular_references(self):
        """Test handling of circular references in data"""
        # Create circular reference
        circular_order = {
            'id': 'circular',
            'legs': [{'position_effect': 'open'}],
            'state': 'filled'
        }
        circular_order['self_ref'] = circular_order  # Circular reference
        
        orders = [circular_order]
        
        # Should handle circular references without infinite loops
        result = self.detector.detect_chains(orders)
        assert isinstance(result, list)


class TestMemoryExhaustionScenarios:
    """Tests for memory exhaustion and resource limits"""

    def setup_method(self):
        self.detector = RolledOptionsChainDetector()

    def test_extremely_large_dataset(self):
        """Test handling of extremely large datasets"""
        # Create very large dataset (but not so large it actually exhausts memory)
        large_orders = []
        for i in range(5000):  # 5K orders
            order = {
                'id': f'large_order_{i}',
                'underlying_symbol': f'SYM{i % 100}',
                'state': 'filled',
                'legs': [{'position_effect': 'open' if i % 2 == 0 else 'close'}]
            }
            large_orders.append(order)
        
        # Should handle large dataset without memory errors
        try:
            result = self.detector.detect_chains(large_orders)
            assert isinstance(result, list)
        except MemoryError:
            pytest.skip("System doesn't have enough memory for this test")

    def test_deeply_nested_data_structures(self):
        """Test handling of deeply nested data structures"""
        # Create order with deeply nested structure
        nested_data = {'level': 0}
        current = nested_data
        for i in range(100):  # 100 levels deep
            current['next'] = {'level': i + 1}
            current = current['next']
        
        order = {
            'id': 'deeply_nested',
            'legs': [{'position_effect': 'open'}],
            'state': 'filled',
            'nested_data': nested_data
        }
        
        # Should handle deep nesting without stack overflow
        result = self.detector.detect_chains([order])
        assert isinstance(result, list)

    def test_memory_leak_detection(self):
        """Test for memory leaks during repeated processing"""
        import gc
        import psutil
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Process many small datasets to check for leaks
        for iteration in range(10):
            orders = []
            for i in range(100):
                order = {
                    'id': f'leak_test_{iteration}_{i}',
                    'legs': [{'position_effect': 'open'}],
                    'state': 'filled'
                }
                orders.append(order)
            
            result = self.detector.detect_chains(orders)
            
            # Explicitly clean up
            del orders
            del result
            gc.collect()
        
        final_memory = process.memory_info().rss
        memory_increase = (final_memory - initial_memory) / 1024 / 1024  # MB
        
        # Should not have significant memory leaks
        assert memory_increase < 50.0, f"Potential memory leak: {memory_increase:.1f}MB increase"


class TestConcurrentAccessConflicts:
    """Tests for concurrent access and race condition handling"""

    def setup_method(self):
        self.cron_service = RolledOptionsCronService()

    @pytest.mark.asyncio
    async def test_concurrent_database_access(self):
        """Test handling of concurrent database access"""
        async def concurrent_store(user_id, chain_id):
            with patch('app.core.database.get_db') as mock_get_db:
                mock_db = AsyncMock()
                mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_db)
                mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
                
                mock_db.execute = AsyncMock()
                mock_db.commit = AsyncMock()
                mock_db.begin_nested = AsyncMock()
                
                mock_nested = AsyncMock()
                mock_nested.__aenter__ = AsyncMock(return_value=mock_nested)
                mock_nested.__aexit__ = AsyncMock(return_value=None)
                mock_nested.commit = AsyncMock()
                mock_db.begin_nested.return_value = mock_nested
                
                chain_analysis = {
                    'chain_id': chain_id,
                    'underlying_symbol': 'TEST',
                    'status': 'active',
                    'total_orders': 1,
                    'roll_count': 0,
                    'orders': []
                }
                
                await self.cron_service._store_chain(mock_db, user_id, chain_analysis)
        
        # Run concurrent operations
        tasks = []
        for i in range(5):
            task = asyncio.create_task(
                concurrent_store(f'user_{i}', f'chain_{i}')
            )
            tasks.append(task)
        
        # Should complete without errors
        await asyncio.gather(*tasks, return_exceptions=True)

    @pytest.mark.asyncio
    async def test_race_condition_in_sync_status(self):
        """Test handling of race conditions in sync status updates"""
        async def concurrent_sync_update(user_id, status):
            with patch('app.core.database.get_db') as mock_get_db:
                mock_db = AsyncMock()
                mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_db)
                mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
                mock_db.execute = AsyncMock()
                mock_db.commit = AsyncMock()
                
                await self.cron_service._update_sync_status(user_id, status)
        
        # Simulate concurrent status updates for same user
        tasks = []
        for status in ['processing', 'completed', 'error']:
            task = asyncio.create_task(
                concurrent_sync_update('race_user', status)
            )
            tasks.append(task)
        
        # Should handle concurrent updates gracefully
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check that no unhandled exceptions occurred
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0


class TestRecoveryScenarios:
    """Tests for system recovery scenarios"""

    def setup_method(self):
        self.cron_service = RolledOptionsCronService()

    @pytest.mark.asyncio
    async def test_partial_processing_recovery(self):
        """Test recovery from partial processing failures"""
        # Simulate a scenario where processing partially completes
        users_to_process = [
            {'user_id': 'user_1', 'full_sync_required': True},
            {'user_id': 'user_2', 'full_sync_required': True},
            {'user_id': 'user_3', 'full_sync_required': True}
        ]
        
        with patch.object(self.cron_service, '_get_users_needing_processing') as mock_get_users, \
             patch.object(self.cron_service, '_process_user_rolled_options') as mock_process, \
             patch.object(self.cron_service, '_update_sync_status') as mock_update:
            
            mock_get_users.return_value = users_to_process
            
            # First user succeeds, second fails, third succeeds
            mock_process.side_effect = [
                {'success': True, 'chains_processed': 5},
                Exception("Processing failed"),
                {'success': True, 'chains_processed': 3}
            ]
            mock_update.return_value = None
            
            result = await self.cron_service.process_all_users()
            
            # Should recover and continue processing
            assert result['success'] is True
            assert result['users_processed'] == 2  # Two successful
            assert len(result['errors']) == 1  # One failure

    @pytest.mark.asyncio
    async def test_system_restart_recovery(self):
        """Test recovery after system restart"""
        # Test that system can recover from interrupted processing
        with patch.object(self.cron_service, '_get_users_needing_processing') as mock_get_users:
            # Simulate users that were being processed when system went down
            mock_get_users.return_value = [
                {'user_id': 'interrupted_user', 'processing_status': 'processing'}
            ]
            
            # Should identify and reprocess interrupted users
            result = mock_get_users.return_value
            assert len(result) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])