"""
Main API router that includes all endpoint routers
"""

from fastapi import APIRouter

from app.api import auth, portfolio, stocks, options, breakdown, rolled_options, rolled_options_debug, rolled_options_v2, sync, scheduler_status, logo

# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Include all route modules
api_router.include_router(auth.router)
api_router.include_router(portfolio.router)
api_router.include_router(stocks.router)
api_router.include_router(options.router)
api_router.include_router(breakdown.router)
api_router.include_router(rolled_options.router)
api_router.include_router(rolled_options_debug.router)
api_router.include_router(rolled_options_v2.router)  # New fast database-driven endpoints
api_router.include_router(sync.router)
api_router.include_router(scheduler_status.router)
api_router.include_router(logo.router)

# Add a simple health check for the API
@api_router.get("/health")
async def api_health():
    """API health check endpoint"""
    return {
        "status": "healthy",
        "message": "Trade Analytics API is running",
        "endpoints": {
            "auth": "/api/v1/auth",
            "portfolio": "/api/v1/portfolio", 
            "stocks": "/api/v1/stocks",
            "options": "/api/v1/options",
            "breakdown": "/api/v1/breakdown",
            "rolled_options": "/api/v1/rolled-options",
            "sync": "/api/v1/sync"
        }
    }