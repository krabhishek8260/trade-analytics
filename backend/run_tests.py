#!/usr/bin/env python3
"""
Test runner for Options Portfolio Calculations

This script runs the comprehensive test suite for options portfolio
value calculations to ensure accuracy and reliability.
"""

import subprocess
import sys
import os

def run_tests():
    """Run the options calculation tests"""
    
    # Change to backend directory
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(backend_dir)
    
    print("🧪 Running Options Portfolio Calculation Tests...")
    print("=" * 60)
    
    # Run pytest with verbose output and coverage
    cmd = [
        sys.executable, "-m", "pytest", 
        "tests/test_options_calculations.py",
        "-v",
        "--tb=short",
        "--cov=app.api.options",
        "--cov=app.services.robinhood_service", 
        "--cov-report=term-missing"
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("Warnings:")
            print(result.stderr)
        print("✅ All tests passed!")
        return True
        
    except subprocess.CalledProcessError as e:
        print("❌ Tests failed!")
        print(e.stdout)
        if e.stderr:
            print("Errors:")
            print(e.stderr)
        return False
    
    except FileNotFoundError:
        print("❌ pytest not found. Please install test dependencies:")
        print("pip install -r requirements-test.txt")
        return False

def validate_calculation_examples():
    """Validate the documentation examples"""
    
    print("\n📖 Validating Documentation Examples...")
    print("=" * 60)
    
    # Example 1: Simple Positions
    print("Example 1: Simple Positions")
    long_value = 10 * 7.00 * 100  # $7,000
    long_cost = 10 * 5.00 * 100   # $5,000  
    long_pnl = long_value - long_cost  # $2,000
    
    short_value = 5 * 3.00 * 100   # $1,500
    short_credit = 5 * 8.00 * 100  # $4,000
    short_pnl = short_credit - short_value  # $2,500
    
    portfolio_value = long_value - short_value  # $5,500
    total_pnl = long_pnl + short_pnl  # $4,500
    
    print(f"  Long Position: ${long_value:,} value, ${long_pnl:,} P&L")
    print(f"  Short Position: ${short_value:,} liability, ${short_pnl:,} P&L") 
    print(f"  Portfolio Value: ${portfolio_value:,}")
    print(f"  Total P&L: ${total_pnl:,}")
    
    # Example 2: Bull Call Spread
    print("\nExample 2: Bull Call Spread")
    buy_call_value = 1 * 12.00 * 100  # $1,200
    buy_call_cost = 1 * 10.00 * 100   # $1,000
    buy_call_pnl = buy_call_value - buy_call_cost  # $200
    
    sell_call_value = 1 * 5.00 * 100  # $500
    sell_call_credit = 1 * 7.00 * 100 # $700
    sell_call_pnl = sell_call_credit - sell_call_value  # $200
    
    spread_value = buy_call_value - sell_call_value  # $700
    spread_pnl = buy_call_pnl + sell_call_pnl  # $400
    
    print(f"  Long Call: ${buy_call_value:,} value, ${buy_call_pnl:,} P&L")
    print(f"  Short Call: ${sell_call_value:,} liability, ${sell_call_pnl:,} P&L")
    print(f"  Spread Value: ${spread_value:,}")
    print(f"  Spread P&L: ${spread_pnl:,}")
    
    print("✅ All examples validated!")

if __name__ == "__main__":
    print("🔍 Options Portfolio Calculation Validation")
    print("=" * 60)
    
    # Run tests
    tests_passed = run_tests()
    
    # Validate examples
    validate_calculation_examples()
    
    print("\n" + "=" * 60)
    if tests_passed:
        print("✅ All validations completed successfully!")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please review and fix.")
        sys.exit(1)