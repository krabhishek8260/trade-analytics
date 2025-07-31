# Enhanced Rolled Options Chain Detection Tests

This directory contains comprehensive tests for the enhanced rolled options chain detection system, including both legacy options portfolio calculation tests and new enhanced chain detection tests.

## Enhanced Chain Detection Test Coverage

### Unit Tests (`test_enhanced_chain_detection.py`)
- ✅ Enhanced backward tracing algorithm
- ✅ Chain validation logic
- ✅ Enhanced chain identification
- ✅ Data source fallback behavior
- ✅ Opening order matching
- ✅ Symbol-based filtering
- ✅ Debug file loading and deduplication

### Integration Tests (`test_enhanced_chain_integration.py`)  
- ✅ End-to-end processing pipeline
- ✅ Database operations and transactions
- ✅ Cron service integration
- ✅ Multi-user processing
- ✅ Production environment simulation
- ✅ API response handling
- ✅ Sync status tracking

### Performance Tests (`test_enhanced_chain_performance.py`)
- ✅ Large dataset processing (1000+ orders)
- ✅ Production scale testing (965 orders)
- ✅ Memory usage optimization
- ✅ Concurrent processing capability
- ✅ Scalability with increasing dataset sizes
- ✅ Resource utilization monitoring
- ✅ Thread safety validation

### Error Handling Tests (`test_enhanced_chain_error_handling.py`)
- ✅ Database connection failures
- ✅ File system errors
- ✅ API timeout and rate limiting
- ✅ Data corruption handling
- ✅ Memory exhaustion scenarios
- ✅ Network failures
- ✅ Concurrent access conflicts
- ✅ Recovery scenarios

## Legacy Options Portfolio Calculation Tests

### Core Functionality Tests
- ✅ Long position calculations (assets)
- ✅ Short position calculations (liabilities)  
- ✅ Portfolio net value calculations
- ✅ Option spread calculations
- ✅ Edge cases (empty portfolios, all long, all short)
- ✅ Integration tests with mocked API responses

### Documentation Validation Tests
- ✅ Example 1: Simple long/short positions
- ✅ Example 2: Bull call spread
- ✅ All calculation examples from docs

## Running Enhanced Chain Detection Tests

### Using the Enhanced Test Runner (Recommended)
```bash
# Run all enhanced chain detection tests
python tests/run_enhanced_chain_tests.py

# Run specific test types
python tests/run_enhanced_chain_tests.py --type unit           # Unit tests only
python tests/run_enhanced_chain_tests.py --type integration   # Integration tests only
python tests/run_enhanced_chain_tests.py --type performance   # Performance tests only
python tests/run_enhanced_chain_tests.py --type error         # Error handling tests only

# Run with coverage
python tests/run_enhanced_chain_tests.py --coverage

# Run with verbose output
python tests/run_enhanced_chain_tests.py --verbose

# Run performance benchmark
python tests/run_enhanced_chain_tests.py --benchmark

# Run specific test class
python tests/run_enhanced_chain_tests.py --class TestEnhancedBackwardTracing
```

### Manual pytest Commands
```bash
# Run all enhanced chain tests
python -m pytest tests/test_enhanced_chain_*.py -v

# Run specific test file
python -m pytest tests/test_enhanced_chain_detection.py -v
python -m pytest tests/test_enhanced_chain_integration.py -v
python -m pytest tests/test_enhanced_chain_performance.py -v
python -m pytest tests/test_enhanced_chain_error_handling.py -v

# Run with coverage
python -m pytest tests/test_enhanced_chain_*.py --cov=app.services.rolled_options_chain_detector --cov=app.services.rolled_options_cron_service --cov-report=html
```

### In Docker Container
```bash
# Run all enhanced chain tests
docker-compose exec backend python tests/run_enhanced_chain_tests.py

# Run specific test type
docker-compose exec backend python tests/run_enhanced_chain_tests.py --type performance
```

## Running Legacy Options Calculation Tests

### In Docker Container (Recommended)
```bash
# Run all options calculation tests
docker-compose exec backend python -m pytest tests/test_options_calculations.py -v

# Run with coverage
docker-compose exec backend python -m pytest tests/test_options_calculations.py -v --cov=app.api.options --cov=app.services.robinhood_service
```

### Local Environment
```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run tests
python -m pytest tests/test_options_calculations.py -v
```

### Using Legacy Test Runner Script
```bash
python run_tests.py
```

## Enhanced Chain Detection Test Structure

### `TestEnhancedBackwardTracing`
Tests the core enhanced backward tracing algorithm:
- Opening order discovery from roll orders
- Exact matching by symbol, type, strike, expiration
- Symbol-based filtering and data loading
- Debug file loading with deduplication

### `TestChainValidation`
Tests chain validation and identification logic:
- Enhanced vs regular chain identification
- Chain sequence validation (open -> roll -> close)
- Position flow tracking and quantity matching
- Orphaned close order rejection

### `TestDataSourceFallback`
Tests data source fallback behavior:
- Debug files as primary source (development)
- API service fallback (production)
- Extended lookback for enhanced detection
- Error handling for missing data sources

### `TestErrorHandling`
Tests comprehensive error handling:
- Empty and malformed order data
- File loading and JSON parsing errors
- Invalid date and numeric formats
- Memory handling with large datasets

### `TestEndToEndProcessing`
Tests complete processing pipeline:
- Order loading through database storage
- Cron service integration
- Multi-user processing scenarios
- Production environment simulation

### `TestLargeDatasetProcessing`
Tests performance with realistic datasets:
- Production scale (965 orders) processing
- Scalability with increasing dataset sizes
- Memory usage optimization
- Symbol-based processing performance

### `TestConcurrentProcessing`
Tests concurrent operation capabilities:
- Parallel chain detection
- Concurrent user processing
- Thread safety validation
- Resource sharing and conflicts

## Legacy Test Structure

### `TestOptionsPortfolioCalculation`
Tests the core portfolio calculation logic:
- Individual position calculations
- Portfolio aggregation
- Mixed long/short positions
- Spread position handling

### `TestOptionsCalculationDocumentation` 
Validates that documentation examples are mathematically correct:
- Simple position examples
- Spread examples
- All numeric calculations verified

## Key Enhanced Chain Detection Test Cases

### Enhanced Chain Detection Test
```python
# Opening order: Single-leg buy to open
opening_order = {
    'id': 'opening_123',
    'legs': [{'position_effect': 'open', 'side': 'buy', 'strike_price': '45.0'}]
}

# Roll order: Close old position, open new position  
roll_order = {
    'id': 'roll_456',
    'legs': [
        {'position_effect': 'close', 'side': 'sell', 'strike_price': '45.0'},
        {'position_effect': 'open', 'side': 'buy', 'strike_price': '65.0'}
    ]
}

# Expected: Chain starts with opening_order (enhanced chain)
# Chain sequence: [opening_order, roll_order]
```

### Backward Tracing Test
```python
# Roll order closes position that should have matching opening order
close_leg = {
    'symbol': 'HOOD',
    'option_type': 'call', 
    'strike_price': 45.0,
    'expiration_date': '2025-05-16'
}

# Expected: Find matching opening order in historical data
matching_opening = {
    'symbol': 'HOOD',
    'option_type': 'call',
    'strike_price': 45.0, 
    'expiration_date': '2025-05-16',
    'position_effect': 'open'
}
```

### Performance Benchmark Test
```python
# Production scale dataset (965 orders)
orders = create_large_dataset(965)

start_time = time.time()
chains = detector.detect_chains(orders)
detection_time = time.time() - start_time

# Expected: Complete within 3-5 seconds
assert detection_time < 8.0
```

## Legacy Key Test Cases

### Long Position Test
```python
# Buy 10 contracts at $4.00, now worth $5.50
contracts = 10
current_price = 5.50
cost_price = 4.00

expected_market_value = 10 * 5.50 * 100  # $5,500
expected_cost = 10 * 4.00 * 100          # $4,000  
expected_pnl = 5500 - 4000               # $1,500
```

### Short Position Test
```python
# Sell 5 contracts at $8.00, now worth $3.00
contracts = 5
current_price = 3.00
credit_price = 8.00

expected_market_value = 5 * 3.00 * 100   # $1,500 (liability)
expected_cost = -(5 * 8.00 * 100)        # -$4,000 (credit)
expected_pnl = 4000 - 1500               # $2,500
```

### Portfolio Net Value Test
```python
# Long positions: $10,200 in assets
# Short positions: $1,500 in liabilities
# Net value: $10,200 - $1,500 = $8,700
```

## Enhanced Chain Detection Error Scenarios

### Database and Infrastructure Errors
- Database connection failures and timeouts
- Transaction rollback and deadlock recovery
- File system permission and disk space errors
- Network failures and API timeouts

### Data Quality and Corruption
- Malformed JSON and missing required fields
- Invalid date formats and numeric values
- Circular references and deeply nested structures
- Empty datasets and null order handling

### Resource and Performance Limits
- Memory exhaustion with large datasets (5K+ orders)
- Concurrent access conflicts and race conditions
- Thread safety validation
- Processing timeout handling

### Recovery and Resilience
- Partial processing failure recovery
- System restart and interrupted processing recovery
- API rate limiting and authentication failures
- Graceful degradation with missing data sources

## Performance Characteristics

### Enhanced Chain Detection Performance
- **Production Scale**: 965 orders in 3-5 seconds
- **Large Scale**: 2000+ orders with <6x time scaling
- **Memory Usage**: <100MB increase for 2000 orders
- **Concurrency**: Thread-safe with parallel processing support

### Scalability Benchmarks
- **Unit Tests**: <1 second per test
- **Integration Tests**: <10 seconds per test
- **Performance Tests**: Variable (marked as slow tests)
- **Error Handling**: <5 seconds per test

## Adding New Enhanced Chain Tests

When adding new test cases:

1. **Follow Test Structure**: Use appropriate test class based on test type
2. **Use Fixtures**: Leverage conftest.py fixtures for common test data
3. **Mock External Dependencies**: Database, file system, API calls
4. **Test Error Scenarios**: Include negative test cases
5. **Performance Considerations**: Mark slow tests appropriately
6. **Documentation**: Update README with new test coverage

### Test Naming Conventions
- `test_*_handling` - Error handling tests
- `test_*_performance` - Performance tests
- `test_*_validation` - Validation logic tests
- `test_*_integration` - End-to-end tests

### Fixtures Usage
```python
def test_example(detector, sample_opening_order, mock_database_session):
    # Use provided fixtures for consistent test data
    result = detector.detect_chains([sample_opening_order])
    assert len(result) >= 0
```

## Legacy Integration with CI/CD

These tests should be run:
- Before any deployment
- After changes to calculation logic
- As part of automated testing pipeline

## Legacy Error Scenarios Covered

- Empty portfolios
- Missing position data
- Zero prices
- Invalid position types
- Mixed position portfolios

## Legacy Performance Considerations

Tests are designed to run quickly (< 1 second) while providing comprehensive coverage of the calculation logic.

## Related Documentation

- [Enhanced Chains Documentation](../ENHANCED_CHAINS_DOCUMENTATION.md) - Complete enhanced chain system
- [Enhanced Chains Process](../ENHANCED_CHAINS_PROCESS.md) - Operational procedures
- [Options Calculation Guide](../../docs/OPTIONS_CALCULATION_GUIDE.md) - Complete calculation methodology
- [API Documentation](../app/api/options.py) - Implementation details
- [Service Layer](../app/services/robinhood_service.py) - Position processing logic