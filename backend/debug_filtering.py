#!/usr/bin/env python3
"""
Debug script to test filtering logic
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent))

def debug_filtering():
    """Debug filtering logic specifically"""
    
    # Load one JSON file
    debug_data_dir = Path(__file__).parent / "debug_data"
    test_file = debug_data_dir / "20250728_050310_options_orders.json"
    
    print(f"=== Debug Filtering Logic ===")
    print(f"Loading from: {test_file}")
    
    with open(test_file, 'r') as f:
        orders = json.load(f)
    
    print(f"Total orders in file: {len(orders)}")
    
    # Test date filtering
    days_back = 30
    cutoff_date = datetime.now() - timedelta(days=days_back)
    print(f"Cutoff date ({days_back} days back): {cutoff_date}")
    
    # Find TSLL orders
    tsll_orders = [order for order in orders if order.get("chain_symbol") == "TSLL"]
    print(f"TSLL orders in file: {len(tsll_orders)}")
    
    if tsll_orders:
        # Check first few TSLL orders
        for i, order in enumerate(tsll_orders[:3]):
            created_at_str = order.get("created_at", "")
            state = order.get("state", "")
            
            print(f"\nTSLL Order {i+1}:")
            print(f"  ID: {order.get('id', 'unknown')}")
            print(f"  Created: {created_at_str}")
            print(f"  State: {state}")
            
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    is_within_range = created_at >= cutoff_date
                    print(f"  Parsed date: {created_at}")
                    print(f"  Within {days_back} days: {is_within_range}")
                except Exception as e:
                    print(f"  Date parsing error: {e}")
    
    # Test full filtering logic
    print(f"\n=== Full Filtering Test ===")
    filtered_count = 0
    
    for order in orders:
        try:
            # Parse created_at date
            created_at_str = order.get("created_at", "")
            if not created_at_str:
                continue
                
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            
            # Filter by date
            if created_at < cutoff_date:
                continue
            
            # Filter by symbol
            chain_symbol = order.get("chain_symbol", "").upper()
            if chain_symbol != "TSLL":
                continue
            
            # Only include filled orders
            if order.get("state") != "filled":
                continue
            
            filtered_count += 1
            
        except Exception as e:
            continue
    
    print(f"Orders passing all filters: {filtered_count}")

if __name__ == "__main__":
    debug_filtering()