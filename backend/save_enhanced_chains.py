#!/usr/bin/env python3
"""
Save enhanced chains to JSON file for inspection and later database insertion
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.rolled_options_chain_detector import RolledOptionsChainDetector

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_all_orders():
    """Load all orders from debug data files"""
    debug_data_dir = Path(__file__).parent / "debug_data"
    options_files = list(debug_data_dir.glob("*options_orders*.json"))
    
    all_orders = []
    
    for file_path in sorted(options_files, reverse=True)[:5]:  # Use 5 most recent files
        try:
            with open(file_path, 'r') as f:
                orders = json.load(f)
                
            # Filter for filled orders only
            filled_orders = [
                order for order in orders 
                if order.get('state') == 'filled'
            ]
            
            all_orders.extend(filled_orders)
                    
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            continue
    
    # Remove duplicates
    seen_ids = set()
    unique_orders = []
    for order in all_orders:
        order_id = order.get('id')
        if order_id and order_id not in seen_ids:
            seen_ids.add(order_id)
            unique_orders.append(order)
    
    logger.info(f"Loaded {len(unique_orders)} unique orders for enhanced chain detection")
    return unique_orders

def save_enhanced_chains():
    """Run enhanced chain detection and save results to JSON"""
    
    # Load all orders
    all_orders = load_all_orders()
    
    # Run enhanced chain detection
    detector = RolledOptionsChainDetector()
    logger.info("Running enhanced chain detection...")
    chains = detector.detect_chains(all_orders)
    
    logger.info(f"Enhanced detection found {len(chains)} chains")
    
    # Analyze chains
    chain_analyses = []
    for chain in chains:
        if not chain:
            continue
        
        try:
            analysis = detector._analyze_chain(chain)
            if analysis:
                chain_analyses.append(analysis)
        except Exception as e:
            logger.error(f"Error analyzing chain: {e}")
            continue
    
    logger.info(f"Successfully analyzed {len(chain_analyses)} chains")
    
    # Save to JSON file
    output_file = Path(__file__).parent / "debug_data" / f"enhanced_chains_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_file, 'w') as f:
        json.dump(chain_analyses, f, indent=2, default=str)
    
    logger.info(f"Saved enhanced chains to {output_file}")
    
    # Show examples of enhanced chains
    opening_order_chains = 0
    for analysis in chain_analyses:
        orders = analysis.get('orders', [])
        if orders:
            first_order = orders[0]
            legs = first_order.get('legs', [])
            if len(legs) == 1 and legs[0].get('position_effect') == 'open':
                opening_order_chains += 1
                if opening_order_chains <= 5:  # Show first 5 examples
                    logger.info(f"✅ Enhanced chain: {analysis['underlying_symbol']} starts with single-leg opening order")
                    logger.info(f"   Opening: ${legs[0].get('strike_price')} {legs[0].get('option_type')} {legs[0].get('expiration_date')} ({analysis['total_orders']} total orders)")
    
    logger.info(f"Summary: {opening_order_chains} out of {len(chain_analyses)} chains now start with single-leg opening orders")

if __name__ == "__main__":
    save_enhanced_chains()