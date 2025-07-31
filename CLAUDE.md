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