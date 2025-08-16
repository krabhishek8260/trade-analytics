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

The application includes comprehensive testing infrastructure covering unit, integration, and end-to-end testing.

#### Frontend Testing

```bash
# Unit and integration tests
cd frontend
npm test                    # Run all tests once
npm run test:watch          # Run tests in watch mode
npm run test:coverage       # Run tests with coverage report

# End-to-End tests
npm run test:e2e           # Run Playwright E2E tests
npm run test:e2e:ui        # Run E2E tests with Playwright UI

# Run all tests (type checking, linting, unit tests, E2E)
npm run test:all
```

#### Backend Testing

```bash
# Backend tests
cd backend && pytest

# Run with coverage
cd backend && pytest --cov=app --cov-report=html
```

### Docker Development

#### Start Local Environment
```bash
# Start all services (PostgreSQL, Redis, Backend, Frontend)
docker-compose up -d

# Check service status
docker-compose ps

# View logs for specific service
docker logs tradeanalytics_backend
docker logs tradeanalytics_frontend

# Access services
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

#### Stop Services
```bash
docker-compose down      # Stop all services
docker-compose down -v   # Stop services and remove volumes
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
Fixed demo user ID for consistent testing: `DEMO_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")`

### Common Patterns

#### ❌ WRONG - Don't generate random UUIDs
This creates different UUIDs each time, causing foreign key errors

#### ✅ CORRECT - Use dependency injection
This provides consistent user identification

#### ❌ WRONG - Hardcoded user assumptions
Assumes user exists without checking

#### ✅ CORRECT - Ensure user exists for operations that need it  
Ensures demo user exists for development

### Background Services

For background services that need user context: Use the consistent demo user ID for background processing

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

## Robinhood API Data Structures

This section documents the data structures and fields used when working with Robinhood API data in the options trading system.

### Options Order Fields

When processing options orders through `RobinhoodService.get_options_orders()`, the following fields are extracted and standardized:

#### Core Order Fields
| Field | Type | Description |
|-------|------|-------------|
| `order_id` | `str` | Unique identifier for the order from Robinhood |
| `state` | `str` | Order state: `filled`, `queued`, `confirmed`, `partially_filled`, `cancelled`, `rejected` |
| `type` | `str` | Order type: typically `limit` for options orders |
| `chain_id` | `str` | Identifier for the options chain this order belongs to |
| `chain_symbol` | `str` | Symbol for the underlying asset (e.g., "AAPL", "TSLA") |

#### Financial Fields
| Field | Type | Description |
|-------|------|-------------|
| `processed_quantity` | `float` | Number of contracts actually filled |
| `processed_premium` | `float` | Total premium processed (processed_quantity * premium) |
| `direction` | `str` | `credit` (received money) or `debit` (paid money) |
| `premium` | `float` | Premium per contract |

#### Strategy Fields
| Field | Type | Description |
|-------|------|-------------|
| `strategy` | `str` | Overall strategy name if multi-leg (e.g., "iron_condor") |
| `opening_strategy` | `str` | Strategy used when opening position |
| `closing_strategy` | `str` | Strategy used when closing position |

#### Timing Fields
| Field | Type | Description |
|-------|------|-------------|
| `created_at` | `str` | ISO timestamp when order was created |
| `updated_at` | `str` | ISO timestamp when order was last updated |

#### Leg Information
| Field | Type | Description |
|-------|------|-------------|
| `legs_count` | `int` | Number of legs in this order (1 for single leg, 2+ for spreads) |
| `legs_details` | `List[Dict]` | Array of leg detail objects (see Leg Fields below) |

### Options Order Leg Fields

Each leg in a multi-leg options order contains the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `leg_index` | `int` | Index of this leg in the order (0-based) |
| `id` | `str` | Unique identifier for this specific leg |
| `side` | `str` | `buy` or `sell` |
| `position_effect` | `str` | `open` (opening new position) or `close` (closing existing position) |
| `option_type` | `str` | `call` or `put` |
| `strike_price` | `float` | Strike price of the option |
| `expiration_date` | `str` | Expiration date in YYYY-MM-DD format |
| `long_strategy_code` | `str` | Internal code for tracking long legs in multi-leg strategies |
| `short_strategy_code` | `str` | Internal code for tracking short legs in multi-leg strategies |

### Usage Notes

#### Field Validation
- Always check if `legs_details` exists and has length > 0 before processing multi-leg orders
- `processed_quantity` and `processed_premium` are only meaningful for `filled` orders
- `chain_symbol` comes directly from API response and represents the underlying symbol

#### Data Relationships
- **Orders vs Positions**: Orders represent trade history; positions represent current holdings
- **Multi-leg Orders**: Use `legs_count` to determine if order is single-leg (1) or multi-leg (2+)
- **Strategy Detection**: Combine `opening_strategy`, `closing_strategy`, and leg details for complex strategy identification

#### Data Represenation
- Show Orders with leg details with relevant data fields.

#### Common Patterns
Check if order is filled, process multi-leg orders by iterating through legs_details

## Database Schema

This section documents the database models and their relationships for options trading data.

### Options Orders Table (`options_orders`)

The options orders table stores historical trading orders with complete API alignment and dual storage strategy.

#### Primary Key & References
| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID` | Primary key (auto-generated) |
| `user_id` | `UUID` | Foreign key to users table |

#### Core Order Fields
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `order_id` | `VARCHAR` | UNIQUE, NOT NULL, INDEXED | Robinhood order ID |
| `state` | `VARCHAR(20)` | NOT NULL, INDEXED | filled, queued, confirmed, partially_filled, cancelled, rejected |
| `type` | `VARCHAR(20)` | NOT NULL | limit, market |
| `chain_id` | `VARCHAR(100)` | NULLABLE, INDEXED | Options chain identifier |
| `chain_symbol` | `VARCHAR(20)` | NULLABLE, INDEXED | Underlying asset symbol (e.g., "AAPL") |

#### Financial Fields
| Field | Type | Description | Usage |
|-------|------|-------------|--------|
| `processed_quantity` | `NUMERIC(12,4)` | Number of contracts actually filled | **Display & Calculations** |
| `processed_premium` | `NUMERIC(12,2)` | Total premium processed (total cost/credit) | **P&L Calculations** |
| `premium` | `NUMERIC(12,4)` | Premium per contract | **Display Only** |
| `direction` | `VARCHAR(6)` | credit (received money) or debit (paid money) | **P&L Direction** |

#### Strategy Fields
| Field | Type | Description |
|-------|------|-------------|
| `strategy` | `VARCHAR(50)` | Overall strategy name (e.g., "iron_condor") |
| `opening_strategy` | `VARCHAR(50)` | Strategy used when opening position |
| `closing_strategy` | `VARCHAR(50)` | Strategy used when closing position |

#### Timing Fields
| Field | Type | Description |
|-------|------|-------------|
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Order creation time from API |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | Order last update time from API |
| `db_created_at` | `TIMESTAMP WITH TIME ZONE` | Database record creation time |
| `db_updated_at` | `TIMESTAMP WITH TIME ZONE` | Database record update time |

#### Leg Information (Dual Storage)
| Field | Type | Description |
|-------|------|-------------|
| `legs_count` | `INTEGER` | Number of legs in this order |
| `legs_details` | `JSONB` | Full legs data array for complex queries |

#### Top-Level Leg Fields (Extracted for Performance)
| Field | Type | Description |
|-------|------|-------------|
| `leg_index` | `INTEGER` | Index of primary leg (0-based) |
| `leg_id` | `VARCHAR` | Unique identifier for primary leg |
| `side` | `VARCHAR(4)` | buy or sell |
| `position_effect` | `VARCHAR(5)` | open or close |
| `option_type` | `VARCHAR(4)` | call or put |
| `strike_price` | `NUMERIC(12,4)` | Strike price of primary leg |
| `expiration_date` | `VARCHAR(10)` | Expiration date (YYYY-MM-DD) |
| `long_strategy_code` | `VARCHAR(100)` | Long leg tracking code |
| `short_strategy_code` | `VARCHAR(100)` | Short leg tracking code |

#### System Fields
| Field | Type | Description |
|-------|------|-------------|
| `raw_data` | `JSONB` | Complete API response for debugging |

### Options Positions Table (`options_positions`)

The options positions table stores current holdings with financial metrics and Greeks.

#### Primary Key & References
| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID` | Primary key (auto-generated) |
| `user_id` | `UUID` | Foreign key to users table |

#### Core Position Fields
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `chain_symbol` | `VARCHAR(20)` | NOT NULL, INDEXED | Underlying asset symbol |
| `option_type` | `VARCHAR(4)` | NOT NULL | call or put |
| `strike_price` | `NUMERIC(12,4)` | NOT NULL, INDEXED | Strike price |
| `expiration_date` | `DATE` | NOT NULL, INDEXED | Option expiration date |

#### Position Details
| Field | Type | Description | Usage |
|-------|------|-------------|--------|
| `quantity` | `NUMERIC(12,4)` | Signed quantity (+long, -short) | **Position Direction** |
| `contracts` | `INTEGER` | Absolute number of contracts | **Display & Calculations** |
| `position_type` | `VARCHAR(5)` | long or short | **Strategy Classification** |

#### Transaction Details
| Field | Type | Description |
|-------|------|-------------|
| `transaction_side` | `VARCHAR(4)` | buy or sell |
| `position_effect` | `VARCHAR(5)` | open or close |
| `direction` | `VARCHAR(6)` | credit or debit |

#### Pricing Information
| Field | Type | Description | Usage |
|-------|------|-------------|--------|
| `average_price` | `NUMERIC(12,4)` | Average price per share | **Display Only** |
| `current_price` | `NUMERIC(12,4)` | Current market price per share | **Display Only** |
| `clearing_cost_basis` | `NUMERIC(12,2)` | Total cost basis from API | **P&L Calculations** |
| `clearing_direction` | `VARCHAR(6)` | credit or debit | **P&L Direction** |

#### Financial Metrics
| Field | Type | Description | Usage |
|-------|------|-------------|--------|
| `market_value` | `NUMERIC(12,2)` | Current market value | **Display & P&L** |
| `total_cost` | `NUMERIC(12,2)` | Total cost paid | **Display & P&L** |
| `total_return` | `NUMERIC(12,2)` | Unrealized P&L | **P&L Calculations** |
| `percent_change` | `NUMERIC(8,4)` | Percentage return | **Display Only** |

#### Greeks & Market Data
| Field | Type | Description |
|-------|------|-------------|
| `delta` | `NUMERIC(8,6)` | Delta exposure |
| `gamma` | `NUMERIC(8,6)` | Gamma exposure |
| `theta` | `NUMERIC(8,6)` | Theta (time decay) |
| `vega` | `NUMERIC(8,6)` | Vega (volatility sensitivity) |
| `rho` | `NUMERIC(8,6)` | Rho (interest rate sensitivity) |
| `implied_volatility` | `NUMERIC(8,4)` | Implied volatility |
| `open_interest` | `INTEGER` | Open interest |

#### Time & System Fields
| Field | Type | Description |
|-------|------|-------------|
| `days_to_expiry` | `INTEGER` | Days until expiration |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Record creation time |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | Record update time |
| `raw_data` | `JSONB` | Complete API response |

### Field Usage Guidelines

#### For P&L Calculations
- **Orders**: Use `processed_premium` and `direction` for accurate P&L
- **Positions**: Use `clearing_cost_basis`, `clearing_direction`, and `total_return`
- **Order State Filter**: **ONLY use orders with `state = 'filled'`** - cancelled, queued, or rejected orders are irrelevant for P&L
- **Never use**: `premium` or `average_price` for calculations

#### For Display Purposes
- **Per-Contract Values**: Use `premium` and `average_price`
- **Contract Counts**: Use `processed_quantity` and `contracts`
- **Percentage Returns**: Use calculated `percent_change`

#### For Queries & Filtering
- **Symbol Filtering**: Use `chain_symbol` (consistent across orders/positions)
- **Date Ranges**: Use `created_at` for orders, `expiration_date` for positions
- **Strategy Analysis**: Use top-level leg fields for performance
- **Multi-Leg Analysis**: Query `legs_details` JSONB for complex conditions

### Data Relationships

#### Orders → Positions Flow
1. Orders represent **trade history** (what happened)
2. Positions represent **current holdings** (what you own now)
3. Use `chain_symbol` + `strike_price` + `expiration_date` + `option_type` to match

#### Key Principles
- **Single Source of Truth**: API data stored exactly as received
- **Dual Storage**: JSONB for flexibility + top-level fields for performance  
- **Calculation Fields**: Clearly separated from display fields
- **Consistent Naming**: Same field names across orders and positions where applicable

### Database Indexing Strategy

The database uses strategic indexing to optimize common query patterns in options trading analysis.

#### Options Orders Indexes

##### Core Query Patterns
- `idx_options_orders_user_created` - User timeline queries (`user_id`, `created_at DESC`)
- `idx_options_orders_user_chain` - Symbol-based filtering (`user_id`, `chain_symbol`)
- `idx_options_orders_user_state` - Order status queries (`user_id`, `state`)

##### Strategy & Chain Tracking  
- `idx_options_orders_chain_id` - Chain relationship queries (`chain_id`)
- `idx_options_orders_strategy` - Strategy analysis (`strategy`)

##### Leg-Based Performance Queries
- `idx_options_orders_user_strike_expiry` - Option matching (`user_id`, `strike_price`, `expiration_date`)
- `idx_options_orders_user_option_type` - Type filtering (`user_id`, `option_type`)
- `idx_options_orders_position_effect` - Open/close analysis (`position_effect`)

#### Options Positions Indexes

##### Core Position Queries
- `idx_options_positions_user_symbol` - Portfolio by symbol (`user_id`, `chain_symbol`)
- `idx_options_positions_user_expiry` - Expiration tracking (`user_id`, `expiration_date`)
- `idx_options_positions_user_updated` - Recent activity (`user_id`, `updated_at DESC`)

##### Analysis & Reporting
- `idx_options_positions_strategy` - Strategy performance (`strategy`)
- `idx_options_positions_type_strike` - Options chain analysis (`option_type`, `strike_price`)
- `idx_options_positions_expiry_range` - Expiration date ranges (`expiration_date`)

#### Index Usage Guidelines

##### High-Performance Queries
User's recent orders, positions by symbol, filled orders for P&L calculation, and P&L history analysis

##### Multi-Column Index Benefits
- **Composite indexes** support queries on any left-most column combination
- **User-prefixed indexes** enable efficient user data isolation
- **Date indexes** optimized for chronological analysis

##### JSONB Query Performance
- Use top-level leg fields for common filtering (indexed)
- Reserve `legs_details` JSONB for complex multi-leg analysis
- Consider GIN indexes on JSONB columns for frequent complex queries

#### Performance Optimization

##### Query Patterns to Prefer
1. **Filter by user first** - All indexes start with `user_id`
2. **Use top-level leg fields** - Faster than JSONB queries
3. **Date range queries** - Leverage chronological indexes

##### Query Patterns to Avoid
1. **Cross-user queries** - Not optimized for multi-tenant access
2. **Full JSONB scans** - Use top-level fields when possible
3. **Non-indexed field sorting** - Will cause full table scans

## Options Order History System

This section documents the comprehensive options order history system implemented to provide users with detailed order tracking, multi-leg strategy visualization, and scalable data synchronization.

### System Architecture

The options order history system uses a **database-first architecture** with API fallback and background synchronization to handle large datasets efficiently.

#### Core Components

1. **Database Layer** (`backend/app/models/options_order.py`)
   - Primary storage for historical options orders
   - Optimized indexes for pagination and filtering
   - JSONB storage for complex multi-leg order data
   - Dual storage strategy: top-level fields for performance + JSONB for flexibility

2. **Service Layer** (`backend/app/services/options_order_service.py`)
   - Enhanced with progress tracking callbacks
   - Pagination support for large datasets
   - Sync status tracking via Redis cache
   - Database-first queries with API fallback

3. **Background Processing** (`backend/app/services/options_orders_background_service.py`)
   - User detection and sync management
   - Progressive sync strategy (full sync for new users, incremental for existing)
   - Error handling and retry logic
   - Real-time progress tracking

4. **Scheduler Integration** (`backend/app/core/scheduler.py`)
   - Automatic periodic sync every 15 minutes
   - Manual trigger capabilities
   - Job execution logging and monitoring

5. **Frontend Components** (`frontend/src/components/OptionsHistorySection.tsx`)
   - Order-based display instead of rolled chains
   - Expandable multi-leg order visualization
   - Real-time sync status and progress indicators
   - Advanced filtering and pagination

### Data Flow Architecture

#### New User Onboarding Flow
1. New user logs in → Frontend displays "Sync Orders" option
2. User triggers sync OR background job detects new user
3. Full sync initiated (365 days of historical data)
4. Progress tracked in Redis, displayed in real-time UI
5. Orders stored in database with complete API alignment
6. Frontend switches to database-first queries

#### Existing User Incremental Updates
1. Background job runs every 15 minutes
2. Detects users with orders older than 1 hour
3. Incremental sync (7 days of recent data)
4. New orders added to database
5. Frontend automatically shows updated data

#### Real-time Data Access Pattern
Frontend Request → Database Query (Primary) → API Fallback (If empty or new user) → Store in Database → Return Combined Results

### API Endpoints

#### Enhanced Orders Endpoint (`/api/v1/options/orders`)
Database-first approach with pagination. Response includes data, pagination info, filters applied, and data source indicator.

#### Sync Control Endpoints
- Get sync status for current user
- Trigger manual sync with optional parameters

### Database Schema Enhancements

#### New Indexes for Performance
Optimized pagination and user queries, JSONB queries for multi-leg analysis, enhanced compound indexes for filtering.

#### Data Storage Strategy

1. **Complete API Alignment**: All Robinhood API fields stored exactly as received
2. **Dual Storage Pattern**: 
   - Top-level fields for common queries (indexed)
   - JSONB `legs_details` for complex multi-leg analysis
   - Raw API data in `raw_data` JSONB for debugging
3. **Performance Optimizations**:
   - Composite indexes on high-traffic query patterns
   - User-prefixed indexes for tenant isolation
   - Separate display vs calculation fields

### Frontend Implementation

#### Component Architecture
OptionsHistorySection with order-based display, expandable multi-leg visualization, real-time sync status integration, advanced filtering, pagination optimization, and progress indicators.

#### Key Features

1. **Order-Centric Display**: Shows individual orders instead of rolled chains
2. **Expandable Legs**: Click orders to see detailed leg information
3. **Real-time Sync**: Live progress updates during background sync
4. **Smart Pagination**: Handles large datasets efficiently
5. **Advanced Filtering**: Symbol, state, strategy with real-time updates
6. **Data Source Transparency**: Shows whether data comes from database or API

#### User Experience Flow
1. User opens Options tab → History section collapsed by default
2. Click to expand → Shows recent orders with summary view
3. Filter/search → Real-time updates with pagination
4. Click order → Expands to show all legs with details
5. Sync controls → Manual refresh or full sync options
6. Progress tracking → Real-time updates during sync operations

### Background Processing Strategy

#### User Detection Logic
Identify users needing sync based on order count and last order timestamp.

#### Sync Strategy Decision Tree
Full sync for users with no orders (365 days), incremental sync for existing users (7 days).

#### Progress Tracking Implementation
Real-time progress via Redis with status, progress percentage, batch information, and timestamps.

### Performance Optimizations

#### Database Query Patterns
Optimized user order queries and multi-leg analysis with JSONB.

#### Frontend Performance Features
1. **Collapsed by Default**: History section starts collapsed to reduce initial load
2. **Lazy Loading**: Legs details only loaded when expanded
3. **Smart Pagination**: Only loads visible data with cursor-based navigation
4. **Debounced Filtering**: Reduces API calls during real-time search
5. **Progress Batching**: Updates UI in batches to avoid flooding

### Error Handling & Reliability

#### Backend Resilience
Timeout protection and retry logic with exponential backoff.

#### Frontend Error States
1. **Sync Failures**: Clear error messages with retry options
2. **Network Issues**: Graceful fallback with cached data
3. **Large Dataset Warnings**: Pagination hints for performance
4. **Background Sync Errors**: Non-blocking notifications

### Testing Patterns

#### Backend Testing
```bash
# Test sync functionality
pytest backend/tests/test_options_orders_sync.py

# Test API endpoints with pagination
pytest backend/tests/test_options_api.py::test_orders_pagination

# Test background job processing
pytest backend/tests/test_background_services.py
```

#### Frontend Testing
```bash
# Component testing
npm test OptionsHistorySection.test.tsx

# Integration testing with mock API
npm test options-history-integration.test.tsx

# Performance testing for large datasets
npm run test:performance
```

### Monitoring & Observability

#### Background Job Monitoring
Job execution logs stored in database with job name, timing, processing counts, status, and error messages.

#### Performance Metrics
- Sync completion times per user
- Database query performance
- API fallback frequency  
- User engagement with history features
- Error rates and retry success

### Future Enhancements

#### Phase 2 Components (Pending)
- `OptionsOrdersList`: Dedicated list component with virtualization
- `OptionsOrderRow`: Reusable order row with consistent styling
- `OptionsOrderLegs`: Specialized multi-leg visualization component

#### Advanced Features (Roadmap)
- WebSocket real-time updates for live order tracking
- Advanced analytics and trade pattern recognition
- Export functionality (CSV, JSON, PDF reports)
- Mobile-optimized responsive design
- Keyboard navigation and accessibility improvements

### Migration Guide

#### From Chain-Based to Order-Based Display
1. **Data Migration**: No database changes required - uses existing data
2. **Component Replacement**: `OptionsHistorySection` completely rewritten
3. **API Changes**: New pagination parameters, enhanced response format
4. **Backward Compatibility**: Legacy API functions maintained for gradual transition

#### Production Deployment Steps
1. Deploy backend changes with new indexes
2. Run database migrations for enhanced indexes
3. Deploy frontend changes with feature flags
4. Monitor background job performance
5. Gradually enable new features per user segment

## Development Patterns & Common Components

This section documents reusable patterns and components implemented in the application that should be used consistently across all features.

### Data Synchronization Patterns

#### Background Sync Architecture
The application uses a standardized pattern for data synchronization that should be followed for all external data sources.

#### Frontend Sync Integration
Standard hooks pattern for sync operations.

### Progress Indicator Components

#### Backend Progress Tracking
All long-running operations should implement progress tracking using Redis.

#### Frontend Progress Components
Use the standardized `SyncProgressIndicator` component.

### New User Onboarding Pattern

#### Onboarding Flow Structure
All new user flows should follow this standardized pattern.

#### Onboarding Data Flow
1. Detect new user (no data in system)
2. Show onboarding modal with clear value proposition
3. Allow skip option for immediate access
4. If user chooses to proceed: Start background process, show real-time progress, handle errors gracefully
5. Complete with success message and next steps
6. Auto-redirect to relevant feature

### Error Handling Patterns

#### Component-Level Error Boundaries
Wrap feature components in error boundaries.

#### API Error Handling
Standardized error handling for API calls.

### Performance Optimization Patterns

#### Virtualized Lists
For large datasets, use virtualization.

#### Pagination with Infinite Scroll
Standard pagination hook for handling large datasets.

### Real-time Updates Patterns

#### Connection Status Monitoring
Always include connection monitoring for real-time features.

#### WebSocket Integration Pattern
Standard WebSocket hook.

### Form Handling Patterns

#### Standard Form Hook
Reusable form management hook.

### Testing Patterns

#### Component Testing
Standard testing approach for all components.

#### API Integration Testing
Standard API testing pattern.

### Accessibility Patterns

#### ARIA and Keyboard Navigation
Standard accessibility implementation.

### Internationalization Patterns

#### Text Externalization
Standard i18n usage pattern.

### Code Quality Guidelines

#### Component Organization
Components organized by feature with barrel exports, main components, hooks, utilities, and types.

#### Naming Conventions
- **Components**: PascalCase (`UserProfile`, `OrdersList`)
- **Hooks**: camelCase starting with 'use' (`useUserData`, `usePagination`)
- **Utilities**: camelCase (`formatCurrency`, `validateEmail`)
- **Constants**: SCREAMING_SNAKE_CASE (`API_BASE_URL`, `DEFAULT_PAGE_SIZE`)
- **Types/Interfaces**: PascalCase (`User`, `ApiResponse`, `OrderData`)

#### Export Patterns
Default export for main component, named exports for utilities and types.

### Deployment & Environment Patterns

#### Feature Flags
Standard feature flag usage.

These patterns ensure consistency, maintainability, and scalability across all application features. Always refer to these patterns when implementing new functionality or refactoring existing code.

## Testing Infrastructure

This section provides comprehensive guidance for testing practices, setup, and patterns used throughout the application.

### Testing Stack Overview

The application uses a modern testing stack with multiple layers of test coverage:

#### Frontend Testing Technologies

- **Jest**: Primary test runner with Next.js integration
- **React Testing Library**: Component testing with user-centric queries
- **Playwright**: End-to-end testing across multiple browsers
- **@testing-library/jest-dom**: Extended DOM matchers
- **Mock Service Worker (MSW)**: API mocking (future implementation)

#### Backend Testing Technologies

- **pytest**: Primary Python test runner
- **Factory Boy**: Test data generation
- **AsyncIOTestCase**: Async testing support
- **HTTPx**: HTTP client testing for FastAPI

### Frontend Testing Setup

#### Configuration Files

The frontend testing is configured through several key files: jest.config.js, jest.setup.js, and playwright.config.ts.

### Test Utilities and Helpers

#### Custom Render Function

The application provides a custom render function that includes necessary providers.

#### Mock Data Structure

Comprehensive mock data is provided for consistent testing.

### Testing Patterns and Best Practices

#### Unit Testing Components

Standard pattern for component unit tests.

#### Integration Testing

Integration tests cover component interactions and API integration.

#### End-to-End Testing

E2E tests cover complete user workflows.

### Running Tests

#### Development Workflow

```bash
# Start development with testing
cd frontend

# Run tests in watch mode during development
npm run test:watch

# Run specific test files
npm test OptionsOrderRow.test.tsx

# Run tests with coverage
npm run test:coverage

# Run E2E tests
npm run test:e2e

# Run specific E2E test
npx playwright test options-history.spec.ts

# Run E2E tests with UI mode for debugging
npm run test:e2e:ui
```

#### Continuous Integration

```bash
# Full test suite for CI/CD
npm run test:all

# This runs:
# 1. TypeScript type checking
# 2. ESLint code quality checks
# 3. Unit and integration tests
# 4. End-to-end tests across browsers
```

### Coverage Requirements

The application maintains strict coverage thresholds:

- **Statements**: 80% minimum
- **Functions**: 70% minimum  
- **Branches**: 70% minimum
- **Lines**: 80% minimum

Coverage reports are generated in HTML format and available at `coverage/lcov-report/index.html`.

### Testing Anti-Patterns to Avoid

#### ❌ Don't Test Implementation Details
Test user-visible behavior, not internal state.

#### ❌ Don't Use Shallow Rendering
Use full rendering with providers for better integration testing.

#### ❌ Don't Mock Everything
Mock only what's necessary to maintain confidence.

### Test Data Management

#### Factory Pattern for Test Data
Create reusable test data factories.

#### Test Data Isolation
- Each test gets fresh mock data
- Tests don't depend on shared state
- Database resets between integration tests
- API mocks are reset in `beforeEach` blocks

### Performance Testing

#### Large Dataset Testing
Test performance with large datasets.

### Accessibility Testing

Include accessibility checks in component tests.

### Test Organization

#### File Structure
Frontend tests organized by component with dedicated test directories.

#### Naming Conventions
- Test files: `ComponentName.test.tsx`
- E2E tests: `feature-name.spec.ts`
- Test utilities: `test-utils/`
- Mock data: `mocks.ts`

This comprehensive testing infrastructure ensures high code quality, prevents regressions, and provides confidence in application functionality across all user workflows.