#!/usr/bin/env python3
"""
Test script to check what user information is available from Robinhood API
"""

import asyncio
import robin_stocks.robinhood as rh
import json
import os
from app.core.config import settings

async def test_robinhood_user_info():
    """Test what user information is available from Robinhood API"""
    
    print("=== Testing Robinhood API User Information ===")
    
    try:
        # Check if we're already authenticated
        print("\n1. Checking if already authenticated...")
        
        # Try to get account profile without logging in
        account_profile = rh.load_account_profile()
        if account_profile:
            print("✓ Already authenticated!")
        else:
            print("✗ Not authenticated, need to login first")
            return
        
        # Get account profile
        print("\n2. Getting account profile...")
        if account_profile:
            print(f"Account profile keys: {list(account_profile.keys())}")
            print("Account profile (first 10 fields):")
            for i, (key, value) in enumerate(account_profile.items()):
                if i >= 10:
                    break
                print(f"  {key}: {value}")
        else:
            print("No account profile data")
        
        # Get user profile
        print("\n3. Getting user profile...")
        user_profile = rh.load_user_profile()
        if user_profile:
            print(f"User profile keys: {list(user_profile.keys())}")
            print("User profile (first 10 fields):")
            for i, (key, value) in enumerate(user_profile.items()):
                if i >= 10:
                    break
                print(f"  {key}: {value}")
        else:
            print("No user profile data")
        
        # Get portfolio profile
        print("\n4. Getting portfolio profile...")
        portfolio_profile = rh.load_portfolio_profile()
        if portfolio_profile:
            print(f"Portfolio profile keys: {list(portfolio_profile.keys())}")
            print("Portfolio profile (first 10 fields):")
            for i, (key, value) in enumerate(portfolio_profile.items()):
                if i >= 10:
                    break
                print(f"  {key}: {value}")
        else:
            print("No portfolio profile data")
        
        # Check if there's a user_id in any of these responses
        print("\n5. Looking for user_id fields...")
        
        if account_profile:
            print("Account profile user/id fields:")
            for key, value in account_profile.items():
                if 'user' in key.lower() or 'id' in key.lower():
                    print(f"  {key}: {value}")
        
        if user_profile:
            print("User profile user/id fields:")
            for key, value in user_profile.items():
                if 'user' in key.lower() or 'id' in key.lower():
                    print(f"  {key}: {value}")
        
        if portfolio_profile:
            print("Portfolio profile user/id fields:")
            for key, value in portfolio_profile.items():
                if 'user' in key.lower() or 'id' in key.lower():
                    print(f"  {key}: {value}")
        
        # Get account ID specifically
        print("\n6. Getting account ID...")
        if account_profile and 'account_number' in account_profile:
            print(f"Account number: {account_profile['account_number']}")
        if account_profile and 'id' in account_profile:
            print(f"Account ID: {account_profile['id']}")
        
        # Get user ID from user profile
        print("\n7. Getting user ID...")
        if user_profile and 'id' in user_profile:
            print(f"User ID: {user_profile['id']}")
        if user_profile and 'user_id' in user_profile:
            print(f"User ID (user_id field): {user_profile['user_id']}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_robinhood_user_info()) 