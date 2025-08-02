"""
Logo proxy endpoint to handle logo requests and avoid CORS issues
"""

import httpx
import asyncio
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from typing import Optional
import logging
import re

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logo", tags=["logo"])

@router.get("/{symbol}")
async def get_logo(
    symbol: str,
    size: Optional[str] = Query("32", description="Logo size (16, 32, 64, 128)")
):
    """
    Proxy logo requests to avoid CORS issues
    """
    try:
        # Clean the symbol
        clean_symbol = re.sub(r'[^A-Z]', '', symbol.upper())
        
        # Try different logo sources
        logo_sources = [
            f"https://logo.clearbit.com/{clean_symbol.lower()}.com?size={size}",
            f"https://logo.clearbit.com/{clean_symbol.lower()}.org?size={size}",
            f"https://finnhub.io/api/logo?symbol={clean_symbol}",
        ]
        
        async with httpx.AsyncClient() as client:
            for source in logo_sources:
                try:
                    response = await client.get(source, timeout=5.0)
                    if response.status_code == 200:
                        content = response.content
                        content_type = response.headers.get('content-type', 'image/png')
                        
                        return Response(
                            content=content,
                            media_type=content_type,
                            headers={
                                'Cache-Control': 'public, max-age=86400',  # 24 hours
                                'Access-Control-Allow-Origin': '*'
                            }
                        )
                except Exception as e:
                    logger.warning(f"Failed to fetch logo from {source}: {e}")
                    continue
        
        # If no logo found, return a simple colored circle
        raise HTTPException(status_code=404, detail="Logo not found")
        
    except Exception as e:
        logger.error(f"Error fetching logo for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") 