#!/usr/bin/env python3
"""
Test the full enhanced chain detection with HOOD data
"""

import sys
import logging
import json
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.rolled_options_chain_detector import RolledOptionsChainDetector

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_hood_orders():
    """Load HOOD orders for testing"""
    debug_data_dir = Path(__file__).parent / "debug_data"
    options_files = list(debug_data_dir.glob("*options_orders*.json"))
    
    hood_orders = []
    
    for file_path in sorted(options_files, reverse=True)[:3]:  # Use first 3 files
        try:
            with open(file_path, 'r') as f:
                orders = json.load(f)
                
            # Filter for HOOD orders
            for order in orders:
                if (order.get('chain_symbol', '').upper() == 'HOOD' and
                    order.get('state') == 'filled'):
                    hood_orders.append(order)
                    
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            continue
    
    # Remove duplicates
    seen_ids = set()
    unique_orders = []
    for order in hood_orders:
        order_id = order.get('id')
        if order_id and order_id not in seen_ids:
            seen_ids.add(order_id)
            unique_orders.append(order)
    
    logger.info(f"Loaded {len(unique_orders)} unique HOOD orders for testing")
    return unique_orders

def test_enhanced_chain_detection():
    """Test the enhanced chain detection with HOOD orders"""
    
    detector = RolledOptionsChainDetector()
    
    # Load HOOD orders
    hood_orders = load_hood_orders()
    
    # Test the enhanced chain detection
    logger.info("Testing enhanced chain detection...")
    chains = detector.detect_chains(hood_orders)
    
    logger.info(f"Found {len(chains)} chains")
    
    # Find HOOD CALL chains
    hood_call_chains = []
    for chain in chains:
        if not chain:
            continue
        
        first_order = chain[0]
        symbol = first_order.get('chain_symbol', '') or first_order.get('underlying_symbol', '')
        
        # Check if this is a HOOD CALL chain
        if symbol.upper() == 'HOOD':
            legs = first_order.get('legs', [])
            for leg in legs:
                if leg.get('option_type', '').lower() == 'call':
                    hood_call_chains.append(chain)
                    break
    
    logger.info(f"Found {len(hood_call_chains)} HOOD CALL chains")
    
    # Analyze the first HOOD CALL chain
    if hood_call_chains:
        chain = hood_call_chains[0]
        logger.info(f"\\nAnalyzing HOOD CALL chain with {len(chain)} orders:")
        
        for i, order in enumerate(chain):
            created_at = order.get('created_at', '')
            order_id = order.get('id', '')
            direction = order.get('direction', '')
            premium = order.get('processed_premium', 0)
            
            legs = order.get('legs', [])
            logger.info(f"  Order {i+1}: {created_at} - {direction} ${premium}")
            logger.info(f"    ID: {order_id}")
            logger.info(f"    Legs: {len(legs)}")
            
            for j, leg in enumerate(legs):
                strike = leg.get('strike_price', 0)
                option_type = leg.get('option_type', '')
                expiration = leg.get('expiration_date', '')
                side = leg.get('side', '')
                position_effect = leg.get('position_effect', '')
                
                logger.info(f"      Leg {j+1}: ${strike} {option_type} {expiration} - {side} {position_effect}")
            logger.info("")
        
        # Check if the first order is actually a single-leg opening order
        first_order = chain[0]
        first_legs = first_order.get('legs', [])
        
        if len(first_legs) == 1 and first_legs[0].get('position_effect') == 'open':
            logger.info("✅ SUCCESS: Chain starts with single-leg opening order!")
            logger.info(f"   Opening order: ${first_legs[0].get('strike_price')} {first_legs[0].get('option_type')} {first_legs[0].get('expiration_date')}")
        else:
            logger.warning("❌ Chain still starts with roll order, backward tracing may not have worked")
    else:
        logger.warning("No HOOD CALL chains found")

if __name__ == "__main__":
    test_enhanced_chain_detection()