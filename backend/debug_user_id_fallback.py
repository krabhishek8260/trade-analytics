#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.append('/Users/abhishek/tradeanalytics-v2/backend')

from app.core.security import get_current_user_id
import uuid

async def test_user_id_fallback():
    """Test how get_current_user_id behaves without authorization"""
    print("=== USER ID FALLBACK BEHAVIOR ===")
    print()
    
    print("Testing get_current_user_id() without Authorization header:")
    print("(This simulates what happens when no JWT token is provided)")
    print()
    
    try:
        # Test without authorization header
        user_id1 = await get_current_user_id(authorization=None)
        print(f"1st call: {user_id1}")
        
        # Test again to see if it's consistent
        user_id2 = await get_current_user_id(authorization=None)
        print(f"2nd call: {user_id2}")
        
        # Test again
        user_id3 = await get_current_user_id(authorization=None)
        print(f"3rd call: {user_id3}")
        
        print()
        if user_id1 == user_id2 == user_id3:
            print("✅ User ID is CONSISTENT across calls")
        else:
            print("❌ User ID is DIFFERENT across calls - this is the problem!")
        
        print()
        print("Expected behavior based on security.py logic:")
        print("1. Try to use hardcoded target user: 13461768-f848-4c04-aea2-46817bc9a3a5")
        print("2. If that user has orders, use that ID")
        print("3. Otherwise, fall back to demo user: 00000000-0000-0000-0000-000000000001")
        
        # Check which user ID is being used
        target_user = uuid.UUID("13461768-f848-4c04-aea2-46817bc9a3a5")
        demo_user = uuid.UUID("00000000-0000-0000-0000-000000000001")
        
        print()
        if user_id1 == target_user:
            print("🎯 Using target user ID (has orders in database)")
        elif user_id1 == demo_user:
            print("🎯 Using demo user ID (fallback)")
        else:
            print(f"❓ Using unexpected user ID: {user_id1}")
            print("   This suggests the logic in get_current_user_id() might be generating random IDs")
        
    except Exception as e:
        print(f"❌ Error testing get_current_user_id(): {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_user_id_fallback())