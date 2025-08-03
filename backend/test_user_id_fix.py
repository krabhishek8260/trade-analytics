#!/usr/bin/env python3
"""
Test script to verify the user ID fix
"""

import asyncio
import uuid
import hashlib
from app.core.security import DEMO_USER_ID

def test_user_id_conversion():
    """Test the user ID conversion logic"""
    
    print("=== Testing User ID Conversion ===")
    
    # Test cases
    test_cases = [
        "d2eae27a-b0c2-42f9-a7c7-ec287176a9fd",  # Valid UUID
        "12345",  # Non-UUID string
        "user_abc123",  # Another non-UUID string
        "00000000-0000-0000-0000-000000000001",  # Demo user ID
    ]
    
    for robinhood_user_id in test_cases:
        print(f"\nTesting: {robinhood_user_id}")
        
        try:
            # Try to parse as UUID first
            user_uuid = uuid.UUID(robinhood_user_id)
            user_id_str = str(user_uuid)
            print(f"  ✓ Valid UUID: {user_id_str}")
        except ValueError:
            # If not a valid UUID, create a deterministic UUID from the string
            hash_obj = hashlib.md5(robinhood_user_id.encode())
            user_uuid = uuid.UUID(hash_obj.hexdigest())
            user_id_str = str(user_uuid)
            print(f"  ✓ Generated UUID from hash: {user_id_str}")
            print(f"    Original: {robinhood_user_id}")
            print(f"    Hash: {hash_obj.hexdigest()}")
        
        # Test consistency
        try:
            user_uuid2 = uuid.UUID(user_id_str)
            print(f"  ✓ UUID is valid and consistent")
        except ValueError:
            print(f"  ✗ UUID is invalid: {user_id_str}")

def test_demo_user_id():
    """Test demo user ID handling"""
    
    print("\n=== Testing Demo User ID ===")
    
    demo_id_str = str(DEMO_USER_ID)
    print(f"Demo user ID: {demo_id_str}")
    
    # Test if it's a valid UUID
    try:
        demo_uuid = uuid.UUID(demo_id_str)
        print(f"✓ Demo user ID is a valid UUID")
    except ValueError:
        print(f"✗ Demo user ID is not a valid UUID")

if __name__ == "__main__":
    test_user_id_conversion()
    test_demo_user_id() 