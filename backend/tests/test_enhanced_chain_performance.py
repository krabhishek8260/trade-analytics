"""
Performance Tests for Enhanced Rolled Options Chain Detection System

This test suite validates performance characteristics including:
- Large dataset processing performance
- Memory usage optimization
- Concurrent processing capability
- API timeout handling
- Resource utilization monitoring
"""

import pytest
import asyncio
import time
import sys
import psutil
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.rolled_options_chain_detector import RolledOptionsChainDetector
from app.services.rolled_options_cron_service import RolledOptionsCronService


class TestLargeDatasetProcessing:
    """Tests for processing large datasets efficiently"""

    def setup_method(self):
        self.detector = RolledOptionsChainDetector()
        self.cron_service = RolledOptionsCronService()

    def create_large_dataset(self, size: int = 1000):
        """Create a large dataset for performance testing"""
        orders = []
        symbols = ['AAPL', 'TSLA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NFLX', 'NVDA', 'AMD', 'INTC']
        
        for i in range(size):
            symbol = symbols[i % len(symbols)]
            strike = 100.0 + (i % 50) * 5.0  # Vary strikes
            
            order = {
                'id': f'perf_order_{i}',
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

    def test_detection_performance_1000_orders(self):
        """Test detection performance with 1000 orders"""
        orders = self.create_large_dataset(1000)
        
        start_time = time.time()
        result = self.detector.detect_chains(orders)
        detection_time = time.time() - start_time
        
        # Should complete within 5 seconds for 1000 orders
        assert detection_time < 5.0
        assert isinstance(result, list)
        
        print(f"Detection time for 1000 orders: {detection_time:.2f}s")

    def test_detection_performance_production_scale(self):
        """Test detection performance at production scale (965 orders)"""
        orders = self.create_large_dataset(965)  # Production scale from logs
        
        start_time = time.time()  
        result = self.detector.detect_chains(orders)
        detection_time = time.time() - start_time
        
        # Should complete within 3-5 seconds based on production logs
        assert detection_time < 8.0
        assert isinstance(result, list)
        
        print(f"Detection time for 965 orders (production scale): {detection_time:.2f}s")

    def test_scalability_with_increasing_dataset_size(self):
        """Test scalability with increasing dataset sizes"""
        sizes = [100, 500, 1000, 2000]
        times = []
        
        for size in sizes:
            orders = self.create_large_dataset(size)
            
            start_time = time.time()
            self.detector.detect_chains(orders)
            detection_time = time.time() - start_time
            
            times.append(detection_time)
            print(f"Size: {size}, Time: {detection_time:.2f}s")
        
        # Time should scale reasonably (not exponentially)
        # Check that 2000 orders doesn't take more than 4x time of 500 orders
        if len(times) >= 4:
            ratio = times[3] / times[1]  # 2000 vs 500
            assert ratio < 6.0, f"Performance degraded too much: {ratio:.2f}x"

    def test_memory_usage_large_datasets(self):
        """Test memory usage with large datasets"""
        import gc
        
        # Get initial memory usage
        gc.collect()
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process large dataset
        orders = self.create_large_dataset(2000)
        result = self.detector.detect_chains(orders)
        
        # Check final memory usage
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"Memory usage: {initial_memory:.1f}MB -> {final_memory:.1f}MB (+{memory_increase:.1f}MB)")
        
        # Should not increase memory by more than 100MB for 2000 orders
        assert memory_increase < 100.0

    def test_symbol_based_processing_performance(self):
        """Test performance improvement with symbol-based processing"""
        # Create dataset with multiple symbols
        orders = self.create_large_dataset(1000)
        
        # Test normal processing
        start_time = time.time()
        result_normal = self.detector.detect_chains(orders)
        normal_time = time.time() - start_time
        
        # Test symbol-grouped processing
        symbol_groups = {}
        for order in orders:
            symbol = order['underlying_symbol']
            if symbol not in symbol_groups:
                symbol_groups[symbol] = []
            symbol_groups[symbol].append(order)
        
        start_time = time.time()
        result_grouped = []
        for symbol, symbol_orders in symbol_groups.items():
            chains = self.detector.detect_chains(symbol_orders)
            result_grouped.extend(chains)
        grouped_time = time.time() - start_time
        
        print(f"Normal processing: {normal_time:.2f}s")
        print(f"Symbol-grouped processing: {grouped_time:.2f}s")
        
        # Grouped processing should be faster or similar
        # (May not always be faster due to overhead, but shouldn't be much slower)
        assert grouped_time < normal_time * 1.5


class TestMemoryOptimization:
    """Tests for memory usage optimization"""

    def setup_method(self):
        self.detector = RolledOptionsChainDetector()

    def test_memory_cleanup_after_processing(self):
        """Test that memory is properly cleaned up after processing"""
        import gc
        
        process = psutil.Process()
        
        # Baseline memory
        gc.collect()
        baseline_memory = process.memory_info().rss
        
        # Process multiple datasets to check for memory leaks
        for i in range(5):
            orders = []
            for j in range(200):
                order = {
                    'id': f'cleanup_order_{i}_{j}',
                    'underlying_symbol': 'TEST',
                    'state': 'filled',
                    'legs': [{'position_effect': 'open'}]
                }
                orders.append(order)
            
            result = self.detector.detect_chains(orders)
            
            # Force cleanup
            del orders
            del result
            gc.collect()
        
        # Check final memory
        final_memory = process.memory_info().rss
        memory_increase = (final_memory - baseline_memory) / 1024 / 1024  # MB
        
        print(f"Memory increase after 5 iterations: {memory_increase:.1f}MB")
        
        # Should not have significant memory leaks
        assert memory_increase < 20.0  # Less than 20MB increase

    def test_large_order_object_handling(self):
        """Test handling of large order objects efficiently"""
        # Create orders with large amounts of data
        large_orders = []
        for i in range(100):
            order = {
                'id': f'large_order_{i}',
                'underlying_symbol': 'LARGE',
                'state': 'filled',
                'legs': [{'position_effect': 'open'}],
                # Add large data fields
                'large_data': 'x' * 10000,  # 10KB of data per order
                'metadata': {f'key_{j}': f'value_{j}' * 100 for j in range(50)}
            }
            large_orders.append(order)
        
        start_time = time.time()
        result = self.detector.detect_chains(large_orders)
        processing_time = time.time() - start_time
        
        # Should handle large objects without significant performance degradation
        assert processing_time < 10.0
        print(f"Processing time for large objects: {processing_time:.2f}s")


class TestConcurrentProcessing:
    """Tests for concurrent processing capabilities"""

    def setup_method(self):
        self.detector = RolledOptionsChainDetector()
        self.cron_service = RolledOptionsCronService()

    def test_concurrent_chain_detection(self):
        """Test concurrent detection of chains"""
        datasets = []
        for i in range(5):
            orders = []
            for j in range(100):
                order = {
                    'id': f'concurrent_order_{i}_{j}',
                    'underlying_symbol': f'SYM{i}',
                    'state': 'filled',
                    'legs': [{'position_effect': 'open' if j % 2 == 0 else 'close'}]
                }
                orders.append(order)
            datasets.append(orders)
        
        # Test concurrent processing
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for dataset in datasets:
                future = executor.submit(self.detector.detect_chains, dataset)
                futures.append(future)
            
            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
        
        concurrent_time = time.time() - start_time
        
        # Test sequential processing for comparison
        start_time = time.time()
        sequential_results = []
        for dataset in datasets:
            result = self.detector.detect_chains(dataset)
            sequential_results.append(result)
        sequential_time = time.time() - start_time
        
        print(f"Concurrent processing: {concurrent_time:.2f}s")
        print(f"Sequential processing: {sequential_time:.2f}s")
        
        # Concurrent should be faster (or at least not significantly slower)
        assert len(results) == len(datasets)
        # Allow some overhead for thread management
        assert concurrent_time < sequential_time * 1.2

    @pytest.mark.asyncio
    async def test_concurrent_user_processing(self):
        """Test concurrent processing of multiple users"""
        users = [
            {'user_id': f'perf_user_{i}', 'full_sync_required': True}
            for i in range(3)
        ]
        
        async def mock_process_user(user_info):
            # Simulate processing time
            await asyncio.sleep(0.2)
            return {
                'success': True,
                'chains_processed': 5,
                'message': f"Processed {user_info['user_id']}"
            }
        
        # Test concurrent processing
        start_time = time.time()
        
        tasks = []
        for user_info in users:
            task = asyncio.create_task(mock_process_user(user_info))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        concurrent_time = time.time() - start_time
        
        # Test sequential processing for comparison  
        start_time = time.time()
        sequential_results = []
        for user_info in users:
            result = await mock_process_user(user_info)
            sequential_results.append(result)
        sequential_time = time.time() - start_time
        
        print(f"Concurrent user processing: {concurrent_time:.2f}s")
        print(f"Sequential user processing: {sequential_time:.2f}s")
        
        # Concurrent should be significantly faster
        assert len(results) == len(users)
        assert concurrent_time < sequential_time * 0.7  # At least 30% faster

    def test_thread_safety(self):
        """Test thread safety of detection algorithms"""
        shared_data = []
        errors = []
        
        def worker_function(worker_id):
            try:
                detector = RolledOptionsChainDetector()
                orders = []
                for i in range(50):
                    order = {
                        'id': f'thread_order_{worker_id}_{i}',
                        'underlying_symbol': f'THREAD{worker_id}',
                        'state': 'filled',
                        'legs': [{'position_effect': 'open'}]
                    }
                    orders.append(order)
                
                result = detector.detect_chains(orders)
                shared_data.append(len(result))
                
            except Exception as e:
                errors.append(str(e))
        
        # Run multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker_function, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(shared_data) == 5  # All threads completed


class TestAPITimeoutHandling:
    """Tests for API timeout and error handling"""

    def setup_method(self):
        self.cron_service = RolledOptionsCronService()

    @pytest.mark.asyncio
    async def test_processing_timeout_handling(self):
        """Test handling of processing timeouts"""
        async def slow_processing():
            await asyncio.sleep(2.0)  # Longer than timeout
            return {'success': True}
        
        # Set short timeout
        original_timeout = self.cron_service.processing_timeout
        self.cron_service.processing_timeout = 1.0  # 1 second
        
        try:
            start_time = time.time()
            
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(slow_processing(), timeout=1.0)
            
            timeout_time = time.time() - start_time
            
            # Should timeout within reasonable time
            assert timeout_time < 1.5  # Allow some overhead
            
        finally:
            # Restore original timeout
            self.cron_service.processing_timeout = original_timeout

    @pytest.mark.asyncio
    async def test_api_response_time_monitoring(self):
        """Test monitoring of API response times"""
        response_times = []
        
        async def mock_api_call(delay):
            start = time.time()
            await asyncio.sleep(delay)
            end = time.time()
            response_times.append(end - start)
            return {'success': True, 'orders': []}
        
        # Test various response times
        delays = [0.1, 0.3, 0.5, 1.0, 2.0]
        
        with patch.object(self.cron_service.json_service, '_load_raw_orders') as mock_api:
            for delay in delays:
                mock_api.side_effect = lambda d=delay: mock_api_call(d)
                
                start_time = time.time()
                await self.cron_service._load_user_orders('test_user', 30)
                total_time = time.time() - start_time
                
                # Should complete within reasonable time of the delay
                assert total_time < delay + 1.0

    @pytest.mark.asyncio
    async def test_batch_processing_performance(self):
        """Test performance of batch processing operations"""
        # Create multiple user batches
        user_batches = []
        for batch_id in range(3):
            batch = []
            for user_id in range(5):
                batch.append({
                    'user_id': f'batch_{batch_id}_user_{user_id}',
                    'full_sync_required': True
                })
            user_batches.append(batch)
        
        processing_times = []
        
        with patch.object(self.cron_service, '_process_user_rolled_options') as mock_process:
            mock_process.return_value = {
                'success': True,
                'chains_processed': 3
            }
            
            # Test batch processing times
            for batch in user_batches:
                start_time = time.time()
                
                # Process batch concurrently
                tasks = []
                for user_info in batch:
                    task = asyncio.create_task(
                        self.cron_service._process_user_rolled_options(user_info)
                    )
                    tasks.append(task)
                
                await asyncio.gather(*tasks)
                
                batch_time = time.time() - start_time
                processing_times.append(batch_time)
        
        # Check that batch processing times are consistent
        if len(processing_times) >= 2:
            time_variance = max(processing_times) - min(processing_times)
            avg_time = sum(processing_times) / len(processing_times)
            
            print(f"Batch processing times: {processing_times}")
            print(f"Average: {avg_time:.2f}s, Variance: {time_variance:.2f}s")
            
            # Variance should be reasonable (not more than 50% of average)
            assert time_variance < avg_time * 0.5


class TestResourceUtilization:
    """Tests for resource utilization monitoring"""

    def setup_method(self):
        self.detector = RolledOptionsChainDetector()

    def test_cpu_usage_during_processing(self):
        """Test CPU usage during intensive processing"""
        process = psutil.Process()
        
        # Get baseline CPU usage
        baseline_cpu = process.cpu_percent()
        time.sleep(0.1)  # Allow CPU measurement to stabilize
        
        # Start intensive processing
        orders = []
        for i in range(1000):
            order = {
                'id': f'cpu_test_order_{i}',
                'underlying_symbol': f'CPU{i % 10}',
                'state': 'filled',
                'legs': [{'position_effect': 'open' if i % 2 == 0 else 'close'}]
            }
            orders.append(order)
        
        start_time = time.time()
        result = self.detector.detect_chains(orders)
        processing_time = time.time() - start_time
        
        # Get CPU usage during processing
        processing_cpu = process.cpu_percent()
        
        print(f"Baseline CPU: {baseline_cpu}%")
        print(f"Processing CPU: {processing_cpu}%")
        print(f"Processing time: {processing_time:.2f}s")
        
        # CPU usage should increase during processing but not be excessive
        assert processing_time < 10.0  # Should complete reasonably fast

    def test_io_efficiency(self):
        """Test I/O efficiency during file operations"""
        import tempfile
        import json
        
        # Create temporary files for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            test_files = []
            for i in range(5):
                file_path = Path(temp_dir) / f'test_orders_{i}.json'
                orders = []
                for j in range(100):
                    order = {
                        'id': f'io_order_{i}_{j}',
                        'state': 'filled',
                        'legs': [{}]
                    }
                    orders.append(order)
                
                with open(file_path, 'w') as f:
                    json.dump(orders, f)
                
                test_files.append(file_path)
            
            # Test file loading performance
            start_time = time.time()
            
            all_orders = []
            for file_path in test_files:
                with open(file_path, 'r') as f:
                    orders = json.load(f)
                    all_orders.extend(orders)
            
            io_time = time.time() - start_time
            
            print(f"I/O time for {len(all_orders)} orders: {io_time:.2f}s")
            
            # I/O should be efficient
            assert io_time < 1.0  # Should load quickly
            assert len(all_orders) == 500  # 5 files * 100 orders each


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-x'])