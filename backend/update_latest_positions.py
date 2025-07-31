#!/usr/bin/env python3
"""
Script to update existing rolled options chains with corrected latest_position information
"""

import asyncio
import json
import os
import sys
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update

# Add the app directory to the path so we can import models
sys.path.insert(0, '/Users/abhishek/tradeanalytics-v2/backend')

from app.models.rolled_options_chain import RolledOptionsChain

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_latest_position_from_chain_data(chain_data):
    """Calculate latest position using the same logic as the fixed service"""
    try:
        orders = chain_data.get('orders', [])
        if not orders:
            return None
        
        # Sort orders chronologically (newest last)
        sorted_orders = sorted(orders, key=lambda x: x.get('created_at', ''))
        most_recent_order = sorted_orders[-1]
        
        # Find the open legs in the most recent order
        legs = most_recent_order.get('legs', [])
        
        # Look for legs with 'open' position effect in the legs array
        open_legs = [leg for leg in legs if leg.get('position_effect') == 'open']
        
        # If no open legs found in legs array, but the order has roll_details, extract from open_position
        if not open_legs and 'roll_details' in most_recent_order:
            roll_details = most_recent_order['roll_details']
            if roll_details.get('type') == 'roll' and 'open_position' in roll_details:
                open_position = roll_details['open_position']
                
                # Create a synthetic leg from roll details
                synthetic_open_leg = {
                    'strike_price': open_position.get('strike_price'),
                    'option_type': open_position.get('option_type', '').lower(),
                    'expiration_date': open_position.get('expiration_date'),
                    'side': open_position.get('side', '').lower(),
                    'position_effect': 'open'
                }
                open_legs = [synthetic_open_leg]
        
        if not open_legs:
            # If no open legs in the most recent order, search backward through the chain
            for i in range(len(sorted_orders) - 2, -1, -1):
                order = sorted_orders[i]
                order_legs = order.get('legs', [])
                order_open_legs = [leg for leg in order_legs if leg.get('position_effect') == 'open']
                
                # Also check roll_details for earlier orders
                if not order_open_legs and 'roll_details' in order:
                    order_roll_details = order['roll_details']
                    if order_roll_details.get('type') == 'roll' and 'open_position' in order_roll_details:
                        open_position = order_roll_details['open_position']
                        synthetic_open_leg = {
                            'strike_price': open_position.get('strike_price'),
                            'option_type': open_position.get('option_type', '').lower(),
                            'expiration_date': open_position.get('expiration_date'),
                            'side': open_position.get('side', '').lower(),
                            'position_effect': 'open'
                        }
                        order_open_legs = [synthetic_open_leg]
                
                if order_open_legs:
                    open_leg = order_open_legs[0]
                    break
            else:
                return None
        else:
            # Use the first open leg as the latest position
            open_leg = open_legs[0]
        
        latest_position = {
            'strike_price': float(open_leg.get('strike_price', 0) or 0),
            'option_type': open_leg.get('option_type', '').upper(),
            'expiration_date': open_leg.get('expiration_date', ''),
            'side': open_leg.get('side', '').lower(),  # buy = long, sell = short
            'quantity': float(most_recent_order.get('quantity', 0) or 0),
            'last_updated': most_recent_order.get('created_at', '')
        }
        
        return latest_position
        
    except Exception as e:
        logger.error(f"Error calculating latest position: {e}")
        return None

async def update_chains():
    """Update all chains with corrected latest_position"""
    
    # Database connection
    engine = create_async_engine(
        'postgresql+asyncpg://postgres:password@localhost:5432/tradeanalytics',
        echo=False
    )
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Get all chains
        result = await session.execute(
            select(RolledOptionsChain)
            .where(RolledOptionsChain.user_id == '123e4567-e89b-12d3-a456-426614174000')
        )
        chains = result.scalars().all()
        
        logger.info(f"Found {len(chains)} chains to update")
        
        updated_count = 0
        for chain in chains:
            try:
                # Calculate latest position from chain data
                latest_position = calculate_latest_position_from_chain_data(chain.chain_data or {})
                
                if latest_position:
                    # Update chain_data with latest_position
                    updated_chain_data = dict(chain.chain_data or {})
                    updated_chain_data['latest_position'] = latest_position
                    
                    # Update the database record
                    stmt = update(RolledOptionsChain).where(
                        RolledOptionsChain.id == chain.id
                    ).values(
                        chain_data=updated_chain_data,
                        updated_at=datetime.utcnow()
                    )
                    await session.execute(stmt)
                    
                    updated_count += 1
                    logger.info(f"Updated {chain.underlying_symbol} chain: {latest_position}")
                else:
                    logger.warning(f"Could not calculate latest position for {chain.underlying_symbol} chain")
                    
            except Exception as e:
                logger.error(f"Error updating chain {chain.chain_id}: {e}")
                continue
        
        # Commit all updates
        await session.commit()
        logger.info(f"Successfully updated {updated_count} chains with latest position data")

if __name__ == "__main__":
    asyncio.run(update_chains())