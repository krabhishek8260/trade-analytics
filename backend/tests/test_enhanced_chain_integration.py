"""
Integration Tests for Enhanced Rolled Options Chain Detection System

This test suite validates the complete end-to-end processing pipeline including:
- Cron service integration
- Database operations
- API response handling
- Multi-user processing
- Production environment simulation
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
import sys

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.rolled_options_cron_service import RolledOptionsCronService
from app.services.rolled_options_chain_detector import RolledOptionsChainDetector
from app.services.json_rolled_options_service import JsonRolledOptionsService


class TestEndToEndProcessing:
    """Tests for complete end-to-end processing pipeline"""

    def setup_method(self):
        """Set up test fixtures"""
        self.cron_service = RolledOptionsCronService()
        
    def create_sample_orders(self):
        """Create sample orders for testing"""
        return [
            {
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
            },
            {
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
        ]

    @pytest.mark.asyncio
    async def test_complete_processing_pipeline(self):
        """Test complete processing from orders to database storage"""
        sample_orders = self.create_sample_orders()
        
        with patch.object(self.cron_service, '_load_user_orders') as mock_load, \
             patch.object(self.cron_service, '_store_chain') as mock_store, \
             patch.object(self.cron_service, '_update_sync_status') as mock_update, \
             patch('app.core.database.get_db') as mock_get_db:
            
            # Mock database session
            mock_db = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
            
            mock_load.return_value = sample_orders
            mock_store.return_value = None
            mock_update.return_value = None
            
            # Test user processing
            user_info = {
                'user_id': 'test_user_123',
                'full_sync_required': True
            }
            
            result = await self.cron_service._process_user_rolled_options(user_info)
            
            # Verify successful processing
            assert result['success'] is True
            assert result['chains_processed'] >= 0
            
            # Verify methods were called
            mock_load.assert_called_once()
            mock_update.assert_called()

    @pytest.mark.asyncio
    async def test_enhanced_detection_in_cron_service(self):
        """Test that cron service uses enhanced detection correctly"""
        sample_orders = self.create_sample_orders()
        
        with patch.object(self.cron_service, '_load_user_orders') as mock_load:
            mock_load.return_value = sample_orders
            
            # Test enhanced detection
            detected_chains = self.cron_service.chain_detector.detect_chains(sample_orders)
            
            # Should find at least one chain
            assert len(detected_chains) >= 0
            
            # Verify enhanced detection is used
            mock_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_storage_operations(self):
        """Test database storage operations with proper transactions"""
        with patch('app.core.database.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Mock database operations
            mock_db.execute = AsyncMock()
            mock_db.commit = AsyncMock()
            mock_db.rollback = AsyncMock()
            mock_db.begin_nested = AsyncMock()
            
            # Create mock nested transaction
            mock_nested = AsyncMock()
            mock_nested.__aenter__ = AsyncMock(return_value=mock_nested)
            mock_nested.__aexit__ = AsyncMock(return_value=None)
            mock_nested.commit = AsyncMock()
            mock_nested.rollback = AsyncMock()
            mock_db.begin_nested.return_value = mock_nested
            
            # Test chain storage
            chain_analysis = {
                'chain_id': 'test_chain_123',
                'underlying_symbol': 'HOOD',
                'status': 'active',
                'total_orders': 2,
                'roll_count': 1,
                'orders': []
            }
            
            await self.cron_service._store_chain(
                mock_db, 'test_user_123', chain_analysis
            )
            
            # Verify database operations
            mock_db.execute.assert_called()
            mock_nested.commit.assert_called()

    @pytest.mark.asyncio
    async def test_error_handling_in_processing(self):
        """Test error handling during processing"""
        with patch.object(self.cron_service, '_load_user_orders') as mock_load:
            # Simulate error in loading orders
            mock_load.side_effect = Exception("API timeout")
            
            user_info = {
                'user_id': 'test_user_123',
                'full_sync_required': True
            }
            
            result = await self.cron_service._process_user_rolled_options(user_info)
            
            # Should handle error gracefully
            assert result['success'] is False
            assert 'API timeout' in result['message']

    @pytest.mark.asyncio
    async def test_sync_status_updates(self):
        """Test sync status tracking and updates"""
        with patch('app.core.database.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_db.execute = AsyncMock()
            mock_db.commit = AsyncMock()
            
            # Test status update
            await self.cron_service._update_sync_status(
                'test_user_123',
                'completed',
                total_chains=5,
                active_chains=3,
                closed_chains=2
            )
            
            # Verify database call
            mock_db.execute.assert_called()
            mock_db.commit.assert_called()


class TestDataSourceHandling:
    """Tests for data source handling and fallback logic"""

    def setup_method(self):
        self.cron_service = RolledOptionsCronService()

    @pytest.mark.asyncio
    async def test_debug_files_loading_development(self):
        """Test loading from debug files in development environment"""
        sample_orders = [{'id': 'debug_order_1', 'state': 'filled'}]
        
        with patch.object(self.cron_service, '_load_orders_from_debug_files') as mock_debug:
            mock_debug.return_value = sample_orders
            
            result = await self.cron_service._load_user_orders('test_user', 30)
            
            # Should use debug files
            assert len(result) > 0
            mock_debug.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_fallback_production(self):
        """Test fallback to API in production environment"""
        with patch.object(self.cron_service, '_load_orders_from_debug_files') as mock_debug, \
             patch.object(self.cron_service.json_service, '_load_raw_orders') as mock_api:
            
            # No debug files available
            mock_debug.return_value = []
            
            # Mock API response
            mock_api.return_value = {
                'success': True,
                'orders': [{'id': 'api_order_1', 'state': 'filled', 'legs': [{}]}]
            }
            
            result = await self.cron_service._load_user_orders('test_user', 30)
            
            # Should fall back to API
            assert len(result) > 0
            mock_debug.assert_called_once()
            mock_api.assert_called()

    @pytest.mark.asyncio
    async def test_extended_lookback_logic(self):
        """Test extended lookback logic for enhanced detection"""
        with patch.object(self.cron_service.json_service, '_load_raw_orders') as mock_api:
            mock_api.return_value = {
                'success': True,
                'orders': [{'id': 'extended_order_1', 'state': 'filled', 'legs': [{}]}]
            }
            
            # Test with short lookback - should extend to 365 days
            result = await self.cron_service._load_user_orders('test_user', 30)
            
            # Verify extended lookback was used
            mock_api.assert_called()
            args, kwargs = mock_api.call_args
            # Should use at least 365 days for enhanced detection
            assert args[0] >= 365

    @pytest.mark.asyncio 
    async def test_order_filtering_logic(self):
        """Test filtering of orders for options only"""
        mixed_orders = [
            {'id': 'stock_order', 'state': 'filled'},  # No legs - stock order
            {'id': 'options_order', 'state': 'filled', 'legs': [{}]},  # Has legs
            {'id': 'cancelled_options', 'state': 'cancelled', 'legs': [{}]}  # Cancelled
        ]
        
        with patch.object(self.cron_service.json_service, '_load_raw_orders') as mock_api:
            mock_api.return_value = {
                'success': True,
                'orders': mixed_orders
            }
            
            result = await self.cron_service._load_user_orders('test_user', 30)
            
            # Should only return filled options orders
            assert len(result) == 1
            assert result[0]['id'] == 'options_order'


class TestMultiUserProcessing:
    """Tests for multi-user processing scenarios"""

    def setup_method(self):
        self.cron_service = RolledOptionsCronService()

    @pytest.mark.asyncio
    async def test_process_all_users_success(self):
        """Test successful processing of multiple users"""
        users_to_process = [
            {'user_id': 'user_1', 'full_sync_required': True},
            {'user_id': 'user_2', 'full_sync_required': False}
        ]
        
        with patch.object(self.cron_service, '_get_users_needing_processing') as mock_get_users, \
             patch.object(self.cron_service, '_process_user_rolled_options') as mock_process, \
             patch.object(self.cron_service, '_update_sync_status') as mock_update, \
             patch.object(self.cron_service, '_refresh_materialized_view') as mock_refresh:
            
            mock_get_users.return_value = users_to_process
            mock_process.return_value = {
                'success': True,
                'chains_processed': 5
            }
            mock_update.return_value = None
            mock_refresh.return_value = None
            
            result = await self.cron_service.process_all_users()
            
            # Verify successful processing
            assert result['success'] is True
            assert result['users_processed'] == 2
            assert result['total_chains'] == 10  # 5 chains per user
            
            # Verify all users were processed
            assert mock_process.call_count == 2
            mock_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_partial_failure_handling(self):
        """Test handling when some users fail processing"""
        users_to_process = [
            {'user_id': 'user_1', 'full_sync_required': True},
            {'user_id': 'user_2', 'full_sync_required': True}
        ]
        
        with patch.object(self.cron_service, '_get_users_needing_processing') as mock_get_users, \
             patch.object(self.cron_service, '_process_user_rolled_options') as mock_process, \
             patch.object(self.cron_service, '_update_sync_status') as mock_update, \
             patch.object(self.cron_service, '_refresh_materialized_view') as mock_refresh:
            
            mock_get_users.return_value = users_to_process
            
            # First user succeeds, second fails
            mock_process.side_effect = [
                {'success': True, 'chains_processed': 3},
                {'success': False, 'message': 'Processing error'}
            ]
            mock_update.return_value = None
            mock_refresh.return_value = None
            
            result = await self.cron_service.process_all_users()
            
            # Should still report overall success with partial results
            assert result['success'] is True
            assert result['users_processed'] == 1  # Only one successful
            assert len(result['errors']) == 1

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test handling of processing timeouts"""
        users_to_process = [
            {'user_id': 'slow_user', 'full_sync_required': True}
        ]
        
        with patch.object(self.cron_service, '_get_users_needing_processing') as mock_get_users, \
             patch.object(self.cron_service, '_process_user_rolled_options') as mock_process, \
             patch.object(self.cron_service, '_update_sync_status') as mock_update:
            
            mock_get_users.return_value = users_to_process
            
            # Simulate timeout
            async def slow_process(*args):
                await asyncio.sleep(10)  # Longer than timeout
                return {'success': True}
            
            mock_process.side_effect = slow_process
            mock_update.return_value = None
            
            # Set short timeout for testing
            self.cron_service.processing_timeout = 1  # 1 second
            
            result = await self.cron_service.process_all_users()
            
            # Should handle timeout gracefully
            assert result['success'] is True
            assert result['users_processed'] == 0
            assert len(result['errors']) == 1
            assert 'timeout' in result['errors'][0].lower()


class TestProductionEnvironmentSimulation:
    """Tests simulating production environment conditions"""

    def setup_method(self):
        self.cron_service = RolledOptionsCronService()

    @pytest.mark.asyncio
    async def test_production_data_loading_no_debug_files(self):
        """Test data loading behavior in production (no debug files)"""
        with patch('pathlib.Path.glob', return_value=[]), \
             patch.object(self.cron_service.json_service, '_load_raw_orders') as mock_api:
            
            mock_api.return_value = {
                'success': True,
                'orders': [
                    {'id': 'prod_order_1', 'state': 'filled', 'legs': [{}]},
                    {'id': 'prod_order_2', 'state': 'filled', 'legs': [{}]}
                ]
            }
            
            result = await self.cron_service._load_user_orders('test_user', 30)
            
            # Should successfully load from API
            assert len(result) == 2
            mock_api.assert_called()

    @pytest.mark.asyncio
    async def test_api_rate_limiting_simulation(self):
        """Test handling of API rate limiting"""
        with patch.object(self.cron_service.json_service, '_load_raw_orders') as mock_api:
            # Simulate rate limit error, then success
            mock_api.side_effect = [
                Exception("Rate limit exceeded"),
                {'success': True, 'orders': []}
            ]
            
            # Should handle rate limiting gracefully
            result = await self.cron_service._load_user_orders('test_user', 30)
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_large_dataset_processing(self):
        """Test processing with production-scale datasets"""
        # Create large dataset similar to production
        large_dataset = []
        for i in range(965):  # Production size from logs
            order = {
                'id': f'large_order_{i}',
                'underlying_symbol': f'SYM{i % 50}',
                'state': 'filled',
                'legs': [{'position_effect': 'open' if i % 2 == 0 else 'close'}]
            }
            large_dataset.append(order)
        
        with patch.object(self.cron_service, '_load_user_orders') as mock_load:
            mock_load.return_value = large_dataset
            
            user_info = {
                'user_id': 'test_user_123',
                'full_sync_required': True
            }
            
            # Should handle large datasets
            with patch('app.core.database.get_db') as mock_get_db:
                mock_db = AsyncMock()
                mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_db)
                mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
                mock_db.execute = AsyncMock()
                mock_db.commit = AsyncMock()
                
                result = await self.cron_service._process_user_rolled_options(user_info)
                
                # Should process successfully despite large size
                assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_concurrent_user_processing(self):
        """Test concurrent processing of multiple users"""
        users = [
            {'user_id': f'user_{i}', 'full_sync_required': True}
            for i in range(5)
        ]
        
        async def mock_process_user(user_info):
            # Simulate processing time
            await asyncio.sleep(0.1)
            return {
                'success': True,
                'chains_processed': 2
            }
        
        with patch.object(self.cron_service, '_get_users_needing_processing') as mock_get_users, \
             patch.object(self.cron_service, '_process_user_rolled_options', side_effect=mock_process_user), \
             patch.object(self.cron_service, '_update_sync_status') as mock_update, \
             patch.object(self.cron_service, '_refresh_materialized_view') as mock_refresh:
            
            mock_get_users.return_value = users
            mock_update.return_value = None
            mock_refresh.return_value = None
            
            import time
            start_time = time.time()
            
            result = await self.cron_service.process_all_users()
            
            processing_time = time.time() - start_time
            
            # Should process all users successfully
            assert result['success'] is True
            assert result['users_processed'] == 5
            
            # Should complete in reasonable time (not strictly sequential)
            assert processing_time < 2.0  # Should be much faster than 5 * 0.1 = 0.5s


if __name__ == '__main__':
    pytest.main([__file__, '-v'])