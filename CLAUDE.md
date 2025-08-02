# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Backend (FastAPI)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev          # Development server
npm run build        # Production build
npm run lint         # ESLint
npm run type-check   # TypeScript checking
npm run format       # Prettier formatting
```

### Testing
```bash
# Backend tests
cd backend && pytest

# Frontend tests  
cd frontend && npm test
```

### Docker Development
```bash
docker-compose up -d     # Start all services
docker-compose down      # Stop services
```

### Database Migrations
```bash
cd backend
alembic upgrade head     # Apply migrations
```

## Architecture Overview

This is a full-stack trading analytics application with the following architecture:

### Backend (FastAPI)
- **Entry Point**: `backend/app/main.py` - FastAPI application with lifespan events for database/Redis initialization
- **API Structure**: RESTful API at `/api/v1/` with modular routers:
  - `/auth` - Authentication endpoints
  - `/portfolio` - Portfolio management and analytics
  - `/stocks` - Stock position tracking
  - `/options` - Options trading analysis and multi-leg strategies
- **Database**: PostgreSQL with SQLAlchemy ORM and async support (asyncpg)
- **Caching**: Redis for performance optimization with configurable TTL
- **Authentication**: Supabase Auth integration with JWT tokens
- **External APIs**: Robinhood API integration via `robin-stocks` library

### Frontend (Next.js 14)
- **Framework**: App Router with TypeScript and Tailwind CSS
- **State Management**: TanStack Query for server state, React Context for app state
- **Authentication**: Supabase Auth Helpers for Next.js
- **UI Components**: Headless UI, Heroicons, and custom components
- **Styling**: Tailwind CSS with dark/light theme support
- **Charts**: Recharts for trading visualizations

### Key Services and Integrations
- **RobinhoodService** (`backend/app/services/robinhood_service.py`): Async wrapper for Robinhood API with caching
- **Database Models**: Separate models for users, portfolios, stock positions, and options orders/positions
- **Real-time Features**: WebSocket support for live price updates
- **Provider Pattern**: React providers for Supabase, React Query, and theme management

### Environment Configuration
- Backend requires: `DATABASE_URL`, `REDIS_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `JWT_SECRET`, `ROBINHOOD_USERNAME`, `ROBINHOOD_PASSWORD`
- Frontend requires: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`

### Development Workflow
1. Use Docker Compose for local development with PostgreSQL and Redis
2. Backend runs on port 8000 with auto-reload
3. Frontend runs on port 3000 with hot reload
4. API documentation available at `/docs` and `/redoc`
5. Health checks available at `/health` and `/api/v1/health`

### Code Quality Tools
- **Backend**: black (formatting), isort (imports), flake8 (linting), mypy (type checking), pytest (testing)
- **Frontend**: ESLint, Prettier, TypeScript compiler
- Always run linting and type checking before commits

## Authentication Patterns

### Overview
The application supports both authenticated and demo modes for development and testing purposes.

### Getting Current User in API Endpoints

**ALWAYS use this pattern for API endpoints that need user identification:**

```python
from fastapi import APIRouter, Depends
from uuid import UUID
from app.core.security import get_current_user_id, ensure_demo_user_exists
from app.core.database import get_db

@router.get("/some-endpoint")
async def some_endpoint(
    current_user_id: UUID = Depends(get_current_user_id),
    db = Depends(get_db),
    # other dependencies...
):
    """Your endpoint that needs user identification"""
    try:
        # Ensure demo user exists for development/testing
        await ensure_demo_user_exists(db)
        
        # Use current_user_id for database operations
        # This will be a consistent UUID for demo mode or actual user ID in production
        
        return {"user_id": str(current_user_id)}
        
    except Exception as e:
        logger.error(f"Error in endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

### Authentication Modes

#### Demo Mode (Development/Testing)
- **No Authorization header**: Returns demo user ID `00000000-0000-0000-0000-000000000001`
- **Authorization: Bearer demo**: Returns demo user ID  
- **Automatic user creation**: `ensure_demo_user_exists()` creates demo user if not exists

#### Production Mode  
- **Authorization: Bearer <jwt_token>**: Validates JWT and returns actual user ID
- **Invalid/missing token**: Returns HTTP 401 Unauthorized

### Key Components

#### `app.core.security.get_current_user_id()`
- **Purpose**: Dependency to get current authenticated user ID
- **Demo mode**: Returns consistent demo UUID when no auth present
- **Production mode**: Validates JWT tokens and returns user UUID
- **Error handling**: Raises HTTPException for invalid authentication

#### `app.core.security.ensure_demo_user_exists()`  
- **Purpose**: Creates demo user in database if it doesn't exist
- **Usage**: Call in endpoints that need user data to exist
- **Safety**: Non-critical function - logs errors but doesn't raise exceptions

#### Demo User Constants
```python
# Fixed demo user ID for consistent testing
DEMO_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
```

### Common Patterns

#### ❌ WRONG - Don't generate random UUIDs
```python
# This creates different UUIDs each time, causing foreign key errors
import uuid
user_id = uuid.uuid4()  # NEVER DO THIS
```

#### ✅ CORRECT - Use dependency injection
```python
# This provides consistent user identification
current_user_id: UUID = Depends(get_current_user_id)
```

#### ❌ WRONG - Hardcoded user assumptions
```python
# Assumes user exists without checking
user_orders = await get_user_orders("some-hardcoded-id")
```

#### ✅ CORRECT - Ensure user exists for operations that need it  
```python
# Ensures demo user exists for development
await ensure_demo_user_exists(db)
user_orders = await get_user_orders(current_user_id)
```

### Background Services

For background services that need user context:

```python
from app.core.security import DEMO_USER_ID

# Use the consistent demo user ID for background processing
result = await background_service.process_user_data(DEMO_USER_ID)
```

### Database Foreign Key Considerations

- All user-related tables have foreign key constraints to `users.id`
- Demo user must exist before creating related records
- Use `ensure_demo_user_exists()` before operations that create user-related data
- Background services should also ensure demo user exists before processing

### Migration to Full Authentication

When implementing full Supabase authentication:

1. Replace demo mode logic with actual JWT validation
2. Update `get_current_user_id()` to always require valid authentication  
3. Remove `ensure_demo_user_exists()` calls from production endpoints
4. Add proper user registration/login flows in frontend

### Testing Authentication

```bash
# Test without authentication (demo mode)
curl http://localhost:8000/api/v1/options/pnl/status

# Test with demo token  
curl -H "Authorization: Bearer demo" http://localhost:8000/api/v1/options/pnl/status

# Test with invalid token (should return 401 in production mode)
curl -H "Authorization: Bearer invalid" http://localhost:8000/api/v1/options/pnl/status
```