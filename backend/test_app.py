#!/usr/bin/env python3
"""
Test script to verify FastAPI application can start
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.main import app
    print("✅ FastAPI application imported successfully")
    
    # Test route collection
    routes = [route.path for route in app.routes]
    print(f"✅ Found {len(routes)} routes:")
    for route in sorted(routes):
        print(f"   {route}")
    
    print("\n✅ Application structure looks good!")
    print("   Ready to start with: uvicorn app.main:app --reload")
    
except Exception as e:
    print(f"❌ Error importing application: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)