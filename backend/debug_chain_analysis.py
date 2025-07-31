#!/usr/bin/env python3
"""
Debug script to test chain analysis for TSLL
"""

import asyncio
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent))

from app.core.database import get_db
from app.models.options_order import OptionsOrder
from app.models.user import User
from app.services.options_order_service import OptionsOrderService
from app.services.robinhood_service import RobinhoodService
from sqlalchemy import select, and_

async def debug_tsll_chains():
    """Debug TSLL chain analysis"""
    
    # Create services
    rh_service = RobinhoodService()
    options_service = OptionsOrderService(rh_service)
    
    user_id = "00000000-0000-0000-0000-000000000001"
    
    print("=== TSLL Chain Analysis Debug ===")
    
    async for db in get_db():
        # Get all TSLL chains
        chains_query = select(
            OptionsOrder.chain_id,
            OptionsOrder.option_type
        ).where(
            and_(
                OptionsOrder.user_id == user_id,
                OptionsOrder.underlying_symbol == "TSLL",
                OptionsOrder.state.notin_(['cancelled', 'canceled', 'rejected', 'failed'])
            )
        ).distinct()
        
        result = await db.execute(chains_query)
        chain_types = result.all()
        
        print(f"Found {len(chain_types)} unique chain+type combinations:")
        
        for chain_id, option_type in chain_types:
            print(f"\n--- Chain {chain_id} ({option_type}) ---")
            
            # Get orders for this specific chain+type
            orders = await options_service.get_orders_by_chain_id_and_type(
                user_id, chain_id, option_type, db
            )
            
            print(f"Orders: {len(orders)}")
            
            # Check for roll orders
            roll_orders = [
                order for order in orders 
                if order.raw_data and 
                isinstance(order.raw_data, dict) and 
                order.raw_data.get("form_source") == "strategy_roll"
            ]
            
            print(f"Roll orders: {len(roll_orders)}")
            
            if len(orders) >= 2:
                # Analyze the chain
                analysis = await options_service._analyze_chain(orders)
                print(f"Is rolled chain: {analysis.get('is_rolled_chain', False)}")
                print(f"Status: {analysis.get('status', 'unknown')}")
                print(f"Net premium: ${analysis.get('net_premium', 0)}")
            else:
                print("Not enough orders for analysis")
                
        break

if __name__ == "__main__":
    asyncio.run(debug_tsll_chains())