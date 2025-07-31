#!/usr/bin/env python3
"""
Debug script to test API query directly
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent))

from app.services.options_order_service import OptionsOrderService
from app.services.robinhood_service import RobinhoodService
from app.models.user import User  # Import User model to resolve relationship

async def debug_api_query():
    """Debug API query directly"""
    
    # Create services exactly like the API does
    rh_service = RobinhoodService()
    options_service = OptionsOrderService(rh_service)
    
    user_id = "00000000-0000-0000-0000-000000000001"
    
    print("=== Direct API Query Debug ===")
    print(f"User ID: {user_id}")
    print(f"Current time: {datetime.now()}")
    print(f"365 days ago: {datetime.now() - timedelta(days=365)}")
    
    # Call the exact same method the API calls
    result = await options_service.get_rolled_options_chains_from_db(
        user_id=user_id,
        days_back=365,
        symbol="TSLL",
        status=None,
        min_orders=2
    )
    
    print(f"\nResult success: {result.get('success')}")
    print(f"Result message: {result.get('message')}")
    
    if result.get("success") and result.get("data"):
        chains = result["data"]["chains"]
        print(f"Chains found: {len(chains)}")
        
        for i, chain in enumerate(chains):
            print(f"\nChain {i+1}:")
            print(f"  ID: {chain['chain_id']}")
            print(f"  Option Type: {chain.get('option_type', 'unknown')}")
            print(f"  Orders: {chain['order_count']}")
            print(f"  Is Rolled: {chain.get('is_rolled_chain', False)}")
    else:
        print("No chains found or error occurred")

if __name__ == "__main__":
    asyncio.run(debug_api_query())