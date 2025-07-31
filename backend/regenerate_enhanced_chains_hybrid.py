#!/usr/bin/env python3
"""
Regenerate chains using enhanced detection (async) but update database synchronously
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from app.models.rolled_options_chain import RolledOptionsChain
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

def regenerate_chains():
    """Regenerate all chains using enhanced detection and update database"""
    
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
    
    # Connect to database with synchronous engine
    logger.info("Connecting to database...")
    engine = create_engine(
        'postgresql://postgres:postgres@localhost:5432/tradeanalytics',
        echo=False
    )
    Session = sessionmaker(bind=engine)
    
    try:
        with Session() as session:
            # Clear existing chains for the test user
            user_id = '123e4567-e89b-12d3-a456-426614174000'
            
            logger.info("Clearing existing chains...")
            result = session.execute(
                delete(RolledOptionsChain).where(RolledOptionsChain.user_id == user_id)
            )
            logger.info(f"Deleted {result.rowcount} existing chains")
            
            # Insert new enhanced chains
            logger.info("Inserting enhanced chains...")
            
            success_count = 0
            for analysis in chain_analyses:
                try:
                    chain_record = RolledOptionsChain(
                        user_id=user_id,
                        chain_id=analysis['chain_id'],
                        underlying_symbol=analysis['underlying_symbol'],
                        status=analysis['status'],
                        initial_strategy=analysis.get('initial_strategy'),
                        start_date=datetime.fromisoformat(analysis['start_date'].replace('Z', '+00:00')) if analysis.get('start_date') else None,
                        last_activity_date=datetime.fromisoformat(analysis['last_activity_date'].replace('Z', '+00:00')) if analysis.get('last_activity_date') else None,
                        total_orders=analysis['total_orders'],
                        roll_count=analysis['roll_count'],
                        total_credits_collected=analysis['total_credits_collected'],
                        total_debits_paid=analysis['total_debits_paid'],
                        net_premium=analysis['net_premium'],
                        total_pnl=analysis['total_pnl'],
                        chain_data={
                            'orders': analysis['orders'],
                            'latest_position': analysis.get('latest_position')
                        }
                    )
                    
                    session.add(chain_record)
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"Error creating chain record for {analysis.get('chain_id', 'unknown')}: {e}")
                    continue
            
            # Commit all changes
            logger.info(f"Committing {success_count} chains to database...")
            session.commit()
            logger.info("✅ Successfully updated database with enhanced chains")
            
            # Check results  
            final_chains = session.query(RolledOptionsChain).filter(
                RolledOptionsChain.user_id == user_id
            ).all()
            
            logger.info(f"Database now contains {len(final_chains)} enhanced chains")
            
            # Show examples of enhanced chains
            opening_order_chains = 0
            for chain in final_chains[:10]:  # Show first 10 examples
                orders = chain.chain_data.get('orders', [])
                if orders:
                    first_order = orders[0]
                    legs = first_order.get('legs', [])
                    if len(legs) == 1 and legs[0].get('position_effect') == 'open':
                        opening_order_chains += 1
                        logger.info(f"✅ Enhanced chain: {chain.underlying_symbol} starts with single-leg opening order")
                        logger.info(f"   Opening: ${legs[0].get('strike_price')} {legs[0].get('option_type')} {legs[0].get('expiration_date')} ({chain.total_orders} total orders)")
                    else:
                        logger.info(f"   Chain: {chain.underlying_symbol} (still starts with roll) - {chain.total_orders} orders")
            
            logger.info(f"🎉 SUCCESS: {opening_order_chains} out of {len(final_chains)} chains now start with single-leg opening orders")
            
    except Exception as e:
        logger.error(f"Database operation failed: {e}")
        raise

if __name__ == "__main__":
    regenerate_chains()