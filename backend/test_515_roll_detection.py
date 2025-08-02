#!/usr/bin/env python3
"""
Test script to verify the 7/31 515 call roll order detection
"""

import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent))

from app.services.rolled_options_chain_detector import RolledOptionsChainDetector

def test_515_call_detection():
    """Test detection of the 7/31 515 call roll order"""
    
    # This is the actual order from 7/31 that was missing from chains
    test_order_missing_form_source = {
        "id": "688b8606-1ab6-4310-bda1-1586f3d0d2e7",
        "form_source": "order_detail",  # NOT "strategy_roll"
        "strategy": "custom",
        "created_at": "2025-07-31T15:04:38.091553Z",
        "legs": [
            {
                "position_effect": "open",
                "side": "sell",
                "option_type": "call",
                "strike_price": "515.0000"
            },
            {
                "position_effect": "close",
                "side": "buy",
                "option_type": "call",
                "strike_price": "495.0000"
            }
        ]
    }
    
    # This order has proper form_source and should be detected by both old and new methods
    test_order_with_form_source = {
        "id": "688b8526-87ab-4633-bfa4-2359d3fb7d95",
        "form_source": "strategy_roll",
        "strategy": "custom",
        "created_at": "2025-07-31T15:00:54.927478Z",
        "legs": [
            {
                "position_effect": "close",
                "side": "buy",
                "option_type": "call",
                "strike_price": "495.0000"
            },
            {
                "position_effect": "open",
                "side": "sell",
                "option_type": "call",
                "strike_price": "515.0000"
            }
        ]
    }
    
    # Test single-leg order (should NOT be detected as roll)
    test_single_leg_order = {
        "id": "test-single-leg",
        "form_source": "order_detail",
        "strategy": "custom",
        "legs": [
            {
                "position_effect": "open",
                "side": "sell",
                "option_type": "call",
                "strike_price": "515.0000"
            }
        ]
    }
    
    # Initialize detector
    detector = RolledOptionsChainDetector()
    
    print("=== Testing 7/31 515 Call Roll Detection ===\n")
    
    # Test 1: Order missing form_source (the problematic one)
    result1 = detector._is_roll_order(test_order_missing_form_source)
    print(f"Test 1 - Order without strategy_roll form_source:")
    print(f"  Order ID: {test_order_missing_form_source['id']}")
    print(f"  form_source: {test_order_missing_form_source['form_source']}")
    print(f"  legs: {len(test_order_missing_form_source['legs'])} (open + close)")
    print(f"  Detected as roll: {result1} ✅" if result1 else f"  Detected as roll: {result1} ❌")
    print()
    
    # Test 2: Order with proper form_source (should still work)
    result2 = detector._is_roll_order(test_order_with_form_source)
    print(f"Test 2 - Order with strategy_roll form_source:")
    print(f"  Order ID: {test_order_with_form_source['id']}")
    print(f"  form_source: {test_order_with_form_source['form_source']}")
    print(f"  Detected as roll: {result2} ✅" if result2 else f"  Detected as roll: {result2} ❌")
    print()
    
    # Test 3: Single-leg order (should NOT be detected as roll)
    result3 = detector._is_roll_order(test_single_leg_order)
    print(f"Test 3 - Single-leg order (should NOT be roll):")
    print(f"  Order ID: {test_single_leg_order['id']}")
    print(f"  legs: {len(test_single_leg_order['legs'])} (only open)")
    print(f"  Detected as roll: {result3} ✅" if not result3 else f"  Detected as roll: {result3} ❌")
    print()
    
    # Test position effects helper method
    print("=== Testing Position Effects Detection ===")
    has_roll_effects1 = detector._has_roll_position_effects(test_order_missing_form_source)
    has_roll_effects2 = detector._has_roll_position_effects(test_single_leg_order)
    
    print(f"Multi-leg order with open+close: {has_roll_effects1} ✅" if has_roll_effects1 else f"Multi-leg order with open+close: {has_roll_effects1} ❌")
    print(f"Single-leg order: {has_roll_effects2} ✅" if not has_roll_effects2 else f"Single-leg order: {has_roll_effects2} ❌")
    print()
    
    # Summary
    all_tests_passed = result1 and result2 and not result3 and has_roll_effects1 and not has_roll_effects2
    print("=== Test Summary ===")
    print(f"All tests passed: {all_tests_passed} ✅" if all_tests_passed else f"Some tests failed: {all_tests_passed} ❌")
    
    if all_tests_passed:
        print("\n🎉 The 7/31 515 call roll order will now be detected!")
        print("The missing form_source issue has been resolved.")
    else:
        print("\n❌ Some tests failed. Check the implementation.")
    
    return all_tests_passed

if __name__ == "__main__":
    test_515_call_detection()