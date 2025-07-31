#!/usr/bin/env python3
"""
Regenerate chains with individual insertion and detailed error handling
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
    
    # Connect to database
    logger.info("Connecting to database...")
    engine = create_engine('postgresql://postgres:postgres@localhost:5432/tradeanalytics')
    Session = sessionmaker(bind=engine)
    
    user_id = '123e4567-e89b-12d3-a456-426614174000'
    
    try:
        with Session() as session:
            # Clear existing chains
            logger.info("Clearing existing chains...")
            result = session.execute(
                delete(RolledOptionsChain).where(RolledOptionsChain.user_id == user_id)
            )
            session.commit()
            logger.info(f"Deleted {result.rowcount} existing chains")
            
            # Insert chains one by one with detailed error handling
            logger.info("Inserting enhanced chains one by one...")
            
            success_count = 0
            failed_count = 0
            
            for i, analysis in enumerate(chain_analyses):
                try:
                    logger.info(f"Inserting chain {i+1}/{len(chain_analyses)}: {analysis.get('underlying_symbol', 'unknown')} - {analysis.get('chain_id', 'unknown')}")
                    
                    # Validate required fields
                    chain_id = analysis.get('chain_id')
                    if not chain_id:
                        logger.error(f"  Missing chain_id, skipping")
                        failed_count += 1
                        continue
                    
                    underlying_symbol = analysis.get('underlying_symbol', 'UNKNOWN')
                    status = analysis.get('status', 'unknown')
                    
                    # Parse dates safely
                    start_date = None
                    if analysis.get('start_date'):
                        try:
                            start_date = datetime.fromisoformat(analysis['start_date'].replace('Z', '+00:00'))
                        except Exception as e:
                            logger.warning(f"  Could not parse start_date: {e}")
                    
                    last_activity_date = None
                    if analysis.get('last_activity_date'):
                        try:
                            last_activity_date = datetime.fromisoformat(analysis['last_activity_date'].replace('Z', '+00:00'))
                        except Exception as e:
                            logger.warning(f"  Could not parse last_activity_date: {e}")
                    
                    # Validate numeric fields
                    total_orders = analysis.get('total_orders', 0)
                    roll_count = analysis.get('roll_count', 0)
                    total_credits_collected = float(analysis.get('total_credits_collected', 0))
                    total_debits_paid = float(analysis.get('total_debits_paid', 0))
                    net_premium = float(analysis.get('net_premium', 0))
                    total_pnl = float(analysis.get('total_pnl', 0))
                    
                    # Prepare chain data (limit size to avoid issues)
                    chain_data = {
                        'orders': analysis.get('orders', [])[:20],  # Limit to first 20 orders
                        'latest_position': analysis.get('latest_position'),
                        'enhanced': True
                    }
                    
                    # Create record
                    chain_record = RolledOptionsChain(
                        user_id=user_id,
                        chain_id=chain_id,
                        underlying_symbol=underlying_symbol,
                        status=status,
                        initial_strategy=analysis.get('initial_strategy'),
                        start_date=start_date,
                        last_activity_date=last_activity_date,
                        total_orders=total_orders,
                        roll_count=roll_count,
                        total_credits_collected=total_credits_collected,
                        total_debits_paid=total_debits_paid,
                        net_premium=net_premium,
                        total_pnl=total_pnl,
                        chain_data=chain_data
                    )
                    
                    session.add(chain_record)
                    session.commit()  # Commit each record individually
                    
                    success_count += 1
                    logger.info(f"  ✅ Successfully inserted")
                    
                    # Check if it's an enhanced chain starting with opening order
                    orders = analysis.get('orders', [])
                    if orders:
                        first_order = orders[0]
                        legs = first_order.get('legs', [])
                        if len(legs) == 1 and legs[0].get('position_effect') == 'open':
                            logger.info(f"  🎉 ENHANCED: Starts with single-leg opening order!")
                            logger.info(f"     Opening: ${legs[0].get('strike_price')} {legs[0].get('option_type')} {legs[0].get('expiration_date')}")
                    
                except Exception as e:
                    failed_count += 1
                    logger.error(f"  ❌ Error inserting chain {analysis.get('chain_id', 'unknown')}: {e}")
                    logger.error(f"     Error type: {type(e).__name__}")
                    try:
                        session.rollback()
                    except:
                        pass
                    continue
            
            logger.info(f"✅ Insertion complete: {success_count} success, {failed_count} failed")
            
            # Final verification
            from sqlalchemy import text
            result = session.execute(text("SELECT COUNT(*) FROM rolled_options_chains WHERE user_id = :user_id"), {"user_id": user_id})
            final_count = result.fetchone()[0]
            logger.info(f"🎉 Database now contains {final_count} enhanced chains")
            
    except Exception as e:
        logger.error(f"Database operation failed: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

if __name__ == "__main__":
    regenerate_chains()