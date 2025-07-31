#!/usr/bin/env python3
"""
Force insert enhanced chains using sync operation with proper commits
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, delete, text
from sqlalchemy.orm import sessionmaker

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from app.models.rolled_options_chain import RolledOptionsChain
from app.services.rolled_options_chain_detector import RolledOptionsChainDetector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_all_orders():
    """Load all orders from debug data files"""
    debug_data_dir = Path(__file__).parent / "debug_data"
    options_files = list(debug_data_dir.glob("*options_orders*.json"))
    
    all_orders = []
    
    for file_path in sorted(options_files, reverse=True)[:5]:
        try:
            with open(file_path, 'r') as f:
                orders = json.load(f)
                
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
    
    logger.info(f"Loaded {len(unique_orders)} unique orders")
    return unique_orders

def force_insert():
    """Force insert enhanced chains with detailed logging"""
    
    # Load and detect chains
    all_orders = load_all_orders()
    detector = RolledOptionsChainDetector()
    
    logger.info("Running enhanced chain detection...")
    chains = detector.detect_chains(all_orders)
    
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
    
    # Connect to database using sync
    engine = create_engine('postgresql://postgres:postgres@localhost:5432/tradeanalytics')
    Session = sessionmaker(bind=engine)
    
    user_id = '123e4567-e89b-12d3-a456-426614174000'
    
    with Session() as session:
        try:
            # Clear existing chains
            logger.info("Clearing existing chains...")
            result = session.execute(
                delete(RolledOptionsChain).where(RolledOptionsChain.user_id == user_id)
            )
            session.commit()
            logger.info(f"Deleted {result.rowcount} existing chains")
            
            # Insert chains one by one with commits
            logger.info(f"Inserting {len(chain_analyses)} enhanced chains...")
            
            success_count = 0
            for i, analysis in enumerate(chain_analyses):
                try:
                    # Parse dates carefully
                    start_date = None
                    if analysis.get('start_date'):
                        try:
                            start_date = datetime.fromisoformat(analysis['start_date'].replace('Z', '+00:00'))
                        except:
                            pass
                    
                    last_activity_date = None
                    if analysis.get('last_activity_date'):
                        try:
                            last_activity_date = datetime.fromisoformat(analysis['last_activity_date'].replace('Z', '+00:00'))
                        except:
                            pass
                    
                    # Create chain record
                    chain_record = RolledOptionsChain(
                        user_id=user_id,
                        chain_id=analysis['chain_id'],
                        underlying_symbol=analysis['underlying_symbol'],
                        status=analysis['status'],
                        initial_strategy=analysis.get('initial_strategy'),
                        start_date=start_date,
                        last_activity_date=last_activity_date,
                        total_orders=analysis['total_orders'],
                        roll_count=analysis['roll_count'],
                        total_credits_collected=float(analysis['total_credits_collected']),
                        total_debits_paid=float(analysis['total_debits_paid']),
                        net_premium=float(analysis['net_premium']),
                        total_pnl=float(analysis['total_pnl']),
                        chain_data={
                            'orders': analysis['orders'],
                            'latest_position': analysis.get('latest_position'),
                            'enhanced': True
                        }
                    )
                    
                    session.add(chain_record)
                    session.commit()  # Commit each individually
                    
                    success_count += 1
                    
                    # Check if enhanced (starts with opening order)
                    orders = analysis.get('orders', [])
                    if orders:
                        first_order = orders[0]
                        legs = first_order.get('legs', [])
                        if len(legs) == 1 and legs[0].get('position_effect') == 'open':
                            logger.info(f"✅ Enhanced chain {i+1}: {analysis['underlying_symbol']} starts with opening order")
                    
                    if (i + 1) % 10 == 0:
                        logger.info(f"Inserted {i+1}/{len(chain_analyses)} chains...")
                    
                except Exception as e:
                    logger.error(f"Failed to insert chain {i+1}: {e}")
                    session.rollback()
                    continue
            
            # Final verification
            result = session.execute(text("SELECT COUNT(*) FROM rolled_options_chains WHERE user_id = :user_id"), {"user_id": user_id})
            final_count = result.fetchone()[0]
            
            logger.info(f"🎉 SUCCESS: Inserted {success_count} chains into database")
            logger.info(f"🎉 Database now contains {final_count} total chains")
            
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            session.rollback()
            raise

if __name__ == "__main__":
    force_insert()