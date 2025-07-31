#!/usr/bin/env python3
"""
Test script for enhanced backward tracing logic
"""

import sys
import logging
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.rolled_options_chain_detector import RolledOptionsChainDetector

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_enhanced_tracing():
    """Test the enhanced backward tracing for HOOD CALL chain"""
    
    detector = RolledOptionsChainDetector()
    
    # Test loading orders for HOOD
    logger.info("Testing _load_all_orders_for_symbol for HOOD...")
    hood_orders = detector._load_all_orders_for_symbol('HOOD')
    logger.info(f"Loaded {len(hood_orders)} orders for HOOD")
    
    # Look for HOOD CALL orders specifically
    hood_call_orders = []
    for order in hood_orders:
        legs = order.get('legs', [])
        for leg in legs:
            if leg.get('option_type', '').lower() == 'call':
                hood_call_orders.append(order)
                break
    
    logger.info(f"Found {len(hood_call_orders)} HOOD CALL orders")
    
    # Test finding specific opening order that should match the chain
    # From database: the earliest roll closes $45 CALL 2025-05-16
    logger.info("Testing _find_matching_opening_order for $45 CALL 2025-05-16...")
    
    matching_order = detector._find_matching_opening_order(
        hood_orders,
        symbol='HOOD',
        option_type='call',
        strike_price=45.0,
        expiration_date='2025-05-16'
    )
    
    if matching_order:
        logger.info(f"SUCCESS: Found matching opening order!")
        logger.info(f"Order ID: {matching_order.get('id')}")
        logger.info(f"Created: {matching_order.get('created_at')}")
        logger.info(f"State: {matching_order.get('state')}")
        logger.info(f"Direction: {matching_order.get('direction')}")
        logger.info(f"Premium: {matching_order.get('processed_premium')}")
        
        legs = matching_order.get('legs', [])
        logger.info(f"Legs count: {len(legs)}")
        for i, leg in enumerate(legs):
            logger.info(f"  Leg {i+1}: ${leg.get('strike_price')} {leg.get('option_type')} {leg.get('expiration_date')} - {leg.get('side')} {leg.get('position_effect')}")
    else:
        logger.warning("No matching opening order found for $45 CALL 2025-05-16")
        
        # Let's see what CALL opening orders we do have
        logger.info("Available HOOD CALL opening orders:")
        call_opens = []
        for order in hood_orders:
            if order.get('state') != 'filled':
                continue
            legs = order.get('legs', [])
            if len(legs) == 1:
                leg = legs[0]
                if (leg.get('option_type', '').lower() == 'call' and 
                    leg.get('position_effect') == 'open'):
                    call_opens.append({
                        'id': order.get('id'),
                        'created_at': order.get('created_at'),
                        'strike': leg.get('strike_price'),
                        'expiration': leg.get('expiration_date'),
                        'side': leg.get('side'),
                        'premium': order.get('processed_premium')
                    })
        
        call_opens.sort(key=lambda x: x['created_at'])
        logger.info(f"Found {len(call_opens)} HOOD CALL opening orders:")
        for i, order in enumerate(call_opens[:10]):
            logger.info(f"  {i+1}. {order['created_at']} - ${order['strike']} CALL {order['expiration']} - {order['side']} open - ${order['premium']}")

if __name__ == "__main__":
    test_enhanced_tracing()