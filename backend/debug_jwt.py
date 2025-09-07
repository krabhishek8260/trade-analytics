#!/usr/bin/env python3

import sys
import os
sys.path.append('/Users/abhishek/tradeanalytics-v2/backend')

from jose import jwt, JWTError
import json
import base64
from app.core.config import settings

def decode_jwt_manual(token_string):
    """Manually decode JWT without verification to see raw contents"""
    try:
        # Split the JWT into its three parts
        header_b64, payload_b64, signature_b64 = token_string.split('.')
        
        # Add padding if needed (base64 requires length to be multiple of 4)
        def add_padding(b64_string):
            missing_padding = len(b64_string) % 4
            if missing_padding:
                b64_string += '=' * (4 - missing_padding)
            return b64_string
        
        header_b64 = add_padding(header_b64)
        payload_b64 = add_padding(payload_b64)
        
        # Decode header and payload
        header = json.loads(base64.urlsafe_b64decode(header_b64))
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        
        return header, payload
        
    except Exception as e:
        print(f"Error manually decoding JWT: {e}")
        return None, None

def debug_jwt_token(auth_header=None):
    """Debug JWT token from Authorization header"""
    
    print("=== JWT TOKEN DEBUG ===")
    print()
    
    if not auth_header:
        print("No Authorization header provided")
        print("Usage: python debug_jwt.py 'Bearer <your-jwt-token>'")
        print("Or copy the Authorization header from your browser's Network tab")
        return
    
    print(f"Authorization header: {auth_header[:50]}...")
    print()
    
    # Extract token
    if not auth_header.startswith("Bearer "):
        print("❌ Invalid Authorization header format. Should start with 'Bearer '")
        return
    
    token = auth_header.split(" ")[1]
    print(f"Raw JWT token: {token[:20]}...{token[-20:]}")
    print()
    
    # Manual decode to see raw contents
    print("1. RAW JWT CONTENTS (without verification):")
    header, payload = decode_jwt_manual(token)
    
    if header and payload:
        print("   Header:")
        print(f"     {json.dumps(header, indent=6)}")
        print("   Payload:")
        print(f"     {json.dumps(payload, indent=6)}")
        print()
        
        # Extract user ID from payload
        user_id = payload.get('sub')
        print(f"   📍 User ID from 'sub' claim: {user_id}")
        
        # Check for other potential user ID fields
        other_fields = {}
        for key, value in payload.items():
            if 'user' in key.lower() or 'id' in key.lower():
                other_fields[key] = value
        
        if other_fields:
            print(f"   📍 Other potential user ID fields: {other_fields}")
        print()
    
    # Try verified decode with our settings
    print("2. VERIFIED JWT DECODE (using app settings):")
    try:
        print(f"   JWT_SECRET configured: {'Yes' if settings.JWT_SECRET else 'No'}")
        print(f"   JWT_ALGORITHM: {settings.JWT_ALGORITHM}")
        
        verified_payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        print("   ✅ JWT verification successful!")
        print(f"   Verified payload: {json.dumps(verified_payload, indent=6)}")
        
        verified_user_id = verified_payload.get('sub')
        print(f"   📍 Verified User ID: {verified_user_id}")
        print()
        
    except JWTError as e:
        print(f"   ❌ JWT verification failed: {e}")
        print("   This could mean:")
        print("   - Wrong JWT_SECRET in settings")
        print("   - Token is expired")
        print("   - Token was signed with different algorithm")
        print("   - Token is malformed")
        print()
    
    # Test our get_current_user_id function
    print("3. TESTING get_current_user_id() FUNCTION:")
    try:
        import asyncio
        from app.core.security import get_current_user_id
        
        async def test_get_user_id():
            try:
                user_id = await get_current_user_id(authorization=auth_header)
                print(f"   ✅ get_current_user_id() returned: {user_id}")
                print(f"   Type: {type(user_id)}")
            except Exception as e:
                print(f"   ❌ get_current_user_id() failed: {e}")
        
        asyncio.run(test_get_user_id())
        
    except Exception as e:
        print(f"   ❌ Error testing get_current_user_id(): {e}")
    
    print()
    print("4. SUPABASE JWT STRUCTURE ANALYSIS:")
    if payload:
        # Check for Supabase-specific fields
        supabase_fields = {
            'aud': payload.get('aud'),  # Audience
            'iss': payload.get('iss'),  # Issuer
            'sub': payload.get('sub'),  # Subject (user ID)
            'email': payload.get('email'),
            'role': payload.get('role'),
            'app_metadata': payload.get('app_metadata'),
            'user_metadata': payload.get('user_metadata'),
            'iat': payload.get('iat'),  # Issued at
            'exp': payload.get('exp'),  # Expires
        }
        
        print("   Supabase-related fields:")
        for field, value in supabase_fields.items():
            if value is not None:
                print(f"     {field}: {value}")
        
        # Check if this looks like a Supabase token
        if payload.get('iss') and 'supabase' in str(payload.get('iss')):
            print("   🎯 This appears to be a Supabase JWT token")
        else:
            print("   ❓ This may not be a standard Supabase token")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        auth_header = sys.argv[1]
    else:
        print("Please provide the Authorization header as an argument:")
        print("python debug_jwt.py 'Bearer <your-token>'")
        print()
        print("To get your JWT token:")
        print("1. Open browser Dev Tools (F12)")
        print("2. Go to Network tab")
        print("3. Make a request to the API (refresh page or click something)")
        print("4. Look for requests to your API (localhost:8000)")
        print("5. Copy the 'Authorization' header value")
        sys.exit(1)
    
    debug_jwt_token(auth_header)