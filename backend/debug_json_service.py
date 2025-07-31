#!/usr/bin/env python3
"""
Debug script to test JSON rolled options service directly
"""

import asyncio
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent))

from app.services.json_rolled_options_service import JsonRolledOptionsService

async def debug_json_service():
    """Debug JSON service directly"""
    
    service = JsonRolledOptionsService()
    
    print("=== JSON Rolled Options Service Debug ===")
    
    # Test with TSLL specifically
    result = await service.get_rolled_chains_from_files(
        days_back=365,
        symbol="TSLL",
        status=None,
        min_orders=2,
        use_cache=False
    )
    
    print(f"Result success: {result.get('success')}")
    print(f"Result message: {result.get('message')}")
    
    if result.get("success") and result.get("data"):
        data = result["data"]
        chains = data.get("chains", [])
        summary = data.get("summary", {})
        
        print(f"\nChains found: {len(chains)}")
        print(f"Summary: {summary}")
        
        for i, chain in enumerate(chains):
            print(f"\nChain {i+1}:")
            print(f"  ID: {chain['chain_id']}")
            print(f"  Symbol: {chain['underlying_symbol']}")
            print(f"  Option Type: {chain.get('option_type', 'unknown')}")
            print(f"  Orders: {chain['order_count']}")
            print(f"  Status: {chain['status']}")
            print(f"  Net Premium: ${chain['net_premium']}")
    else:
        print("No chains found or error occurred")
    
    # Also test without symbol filter to see all chains
    print("\n=== Testing without symbol filter ===")
    result_all = await service.get_rolled_chains_from_files(
        days_back=30,
        symbol=None,
        status=None,
        min_orders=2,
        use_cache=False
    )
    
    if result_all.get("success"):
        all_chains = result_all["data"]["chains"]
        print(f"Total chains found (all symbols): {len(all_chains)}")
        
        # Show symbols found
        symbols = set(chain["underlying_symbol"] for chain in all_chains)
        print(f"Symbols found: {sorted(symbols)}")
        
        # Check if TSLL is in there
        tsll_chains = [c for c in all_chains if c["underlying_symbol"] == "TSLL"]
        print(f"TSLL chains in all results: {len(tsll_chains)}")

if __name__ == "__main__":
    asyncio.run(debug_json_service())