#!/usr/bin/env python3
"""
Test runner for Enhanced Chain Detection test suite

This script runs all enhanced chain detection tests with proper configuration
and provides detailed reporting of test results.
"""

import sys
import subprocess
import argparse
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_tests(test_type='all', verbose=False, coverage=False, parallel=False):
    """
    Run the enhanced chain detection test suite
    
    Args:
        test_type: Type of tests to run ('all', 'unit', 'integration', 'performance', 'error')
        verbose: Enable verbose output
        coverage: Enable coverage reporting
        parallel: Enable parallel test execution
    """
    
    # Base pytest command
    cmd = ['python', '-m', 'pytest']
    
    # Add test files based on type
    test_files = []
    if test_type == 'all':
        test_files = [
            'tests/test_enhanced_chain_detection.py',
            'tests/test_enhanced_chain_integration.py', 
            'tests/test_enhanced_chain_performance.py',
            'tests/test_enhanced_chain_error_handling.py'
        ]
    elif test_type == 'unit':
        test_files = ['tests/test_enhanced_chain_detection.py']
    elif test_type == 'integration':
        test_files = ['tests/test_enhanced_chain_integration.py']
    elif test_type == 'performance':
        test_files = ['tests/test_enhanced_chain_performance.py']
    elif test_type == 'error':
        test_files = ['tests/test_enhanced_chain_error_handling.py']
    else:
        print(f"Unknown test type: {test_type}")
        return 1
    
    cmd.extend(test_files)
    
    # Add options
    if verbose:
        cmd.append('-v')
    
    if coverage:
        cmd.extend([
            '--cov=app.services.rolled_options_chain_detector',
            '--cov=app.services.rolled_options_cron_service', 
            '--cov-report=html',
            '--cov-report=term-missing'
        ])
    
    if parallel:
        cmd.extend(['-n', 'auto'])  # Requires pytest-xdist
    
    # Add markers for filtering
    cmd.extend([
        '--tb=short',  # Shorter traceback format
        '--strict-markers',  # Strict marker validation
    ])
    
    print(f"Running command: {' '.join(cmd)}")
    print("-" * 60)
    
    # Run the tests
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
        return result.returncode
    except KeyboardInterrupt:
        print("\nTest execution interrupted by user")
        return 130
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


def run_specific_test_class(test_class, verbose=False):
    """Run a specific test class"""
    cmd = [
        'python', '-m', 'pytest',
        '-v' if verbose else '',
        '-k', test_class
    ]
    cmd = [c for c in cmd if c]  # Remove empty strings
    
    print(f"Running test class: {test_class}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
        return result.returncode
    except Exception as e:
        print(f"Error running test class: {e}")
        return 1


def run_performance_benchmark():
    """Run performance benchmark tests"""
    cmd = [
        'python', '-m', 'pytest',
        'tests/test_enhanced_chain_performance.py',
        '-v',
        '-m', 'performance',
        '--tb=short'
    ]
    
    print("Running performance benchmark tests...")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
        return result.returncode
    except Exception as e:
        print(f"Error running performance tests: {e}")
        return 1


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Run Enhanced Chain Detection test suite',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_enhanced_chain_tests.py                    # Run all tests
  python run_enhanced_chain_tests.py --type unit        # Run only unit tests
  python run_enhanced_chain_tests.py --type performance # Run only performance tests
  python run_enhanced_chain_tests.py --coverage         # Run with coverage
  python run_enhanced_chain_tests.py --benchmark        # Run performance benchmark
  python run_enhanced_chain_tests.py --class TestEnhancedBackwardTracing
        """
    )
    
    parser.add_argument(
        '--type', 
        choices=['all', 'unit', 'integration', 'performance', 'error'],
        default='all',
        help='Type of tests to run (default: all)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--coverage',
        action='store_true',
        help='Enable coverage reporting'
    )
    
    parser.add_argument(
        '--parallel',
        action='store_true',
        help='Enable parallel test execution'
    )
    
    parser.add_argument(
        '--class',
        dest='test_class',
        help='Run specific test class'
    )
    
    parser.add_argument(
        '--benchmark',
        action='store_true',
        help='Run performance benchmark tests'
    )
    
    args = parser.parse_args()
    
    print("Enhanced Chain Detection Test Suite")
    print("=" * 60)
    
    # Check if required packages are installed
    try:
        import pytest
        import pytest_asyncio
        print(f"✓ pytest version: {pytest.__version__}")
    except ImportError as e:
        print(f"✗ Missing required package: {e}")
        print("Please install test dependencies: pip install -r requirements-test.txt")
        return 1
    
    # Run specific test class if requested
    if args.test_class:
        return run_specific_test_class(args.test_class, args.verbose)
    
    # Run performance benchmark if requested
    if args.benchmark:
        return run_performance_benchmark()
    
    # Run tests based on arguments
    return run_tests(
        test_type=args.type,
        verbose=args.verbose,
        coverage=args.coverage,
        parallel=args.parallel
    )


if __name__ == '__main__':
    sys.exit(main())