# Trading Analytics v2

Modern trading analytics application built with FastAPI, Next.js, and Supabase.

## Tech Stack

- **Backend**: FastAPI (Python) with async/await
- **Frontend**: Next.js 14 with TypeScript and Tailwind CSS
- **Database**: Supabase (PostgreSQL)
- **Authentication**: Supabase Auth
- **Real-time**: WebSocket integration
- **Caching**: Redis for performance
- **Deployment**: Docker containers

## Documentation

### Core Features

- [**New Data Detection System**](docs/NEW_DATA_DETECTION.md) - Smart background data checking without page refreshes
- [**Options Calculation Guide**](docs/OPTIONS_CALCULATION_GUIDE.md) - Detailed options P&L calculations
- [**P&L Analytics Plan**](docs/OPTIONS_PNL_ANALYTICS_PLAN.md) - Comprehensive P&L analysis features
- [**Database Migrations**](backend/docs/DATABASE_MIGRATIONS.md) - Database schema and migration process

### Development Guides

- [**Enhanced Chains Documentation**](backend/ENHANCED_CHAINS_DOCUMENTATION.md) - Options chain analysis
- [**Roll Detection Logic**](backend/ROLL_DETECTION_LOGIC.md) - Rolled options detection
- [**Migration Quick Reference**](backend/docs/MIGRATION_QUICK_REFERENCE.md) - Quick migration commands

## Features

- 📊 Real-time portfolio tracking
- 📈 Advanced options trading analysis
- 🎯 Multi-leg strategy visualization
- 📱 Mobile-responsive design
- ⚡ Real-time price updates
- 🔐 Secure authentication
- 📄 Export capabilities
- 🌙 Dark/light theme support

## Quick Start

### Prerequisites

Before you begin, ensure you have the following installed:

#### Required Software

1. **Docker Desktop** (Recommended for easiest setup)
   - macOS: [Download Docker Desktop for Mac](https://www.docker.com/products/docker-desktop)
   - Windows: [Download Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)
   - Linux: [Install Docker Engine](https://docs.docker.com/engine/install/)

2. **Node.js 18+** (for frontend development)
   - Download from [nodejs.org](https://nodejs.org/)
   - Or install via [nvm](https://github.com/nvm-sh/nvm):
     ```bash
     nvm install 18
     nvm use 18
     ```

3. **Python 3.11+** (for backend development)
   - macOS: `brew install python@3.11`
   - Windows: [Download from python.org](https://www.python.org/downloads/)
   - Linux: `sudo apt install python3.11`

4. **Git**
   - macOS: `brew install git` or included with Xcode Command Line Tools
   - Windows: [Download Git for Windows](https://git-scm.com/download/win)
   - Linux: `sudo apt install git`

### Local Setup

#### Option 1: Docker (Recommended - Easiest)

This method runs everything in containers and requires minimal setup. **Perfect for first-time setup!**

**Step-by-step setup from scratch:**

1. **Install Docker Desktop**
   - Download and install Docker Desktop for your OS (see Prerequisites above)
   - **Important**: Start Docker Desktop and wait for it to be running (you'll see the Docker icon in your menu bar/system tray)

2. **Clone the repository:**
   ```bash
   git clone https://github.com/krabhishek8260/trade-analytics.git
   cd trade-analytics
   ```

3. **Create environment files (optional but recommended):**

   Create `backend/.env` with minimal configuration:
   ```bash
   # Create the backend .env file
   cat > backend/.env << 'EOF'
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/tradeanalytics
   REDIS_URL=redis://localhost:6379
   JWT_SECRET=local-dev-secret-key-change-in-production
   EOF
   ```

   Create `frontend/.env.local` (optional):
   ```bash
   # Create the frontend .env.local file
   cat > frontend/.env.local << 'EOF'
   NEXT_PUBLIC_API_URL=http://localhost:8000
   EOF
   ```

   **Note:** You can skip this step and the app will use defaults from `docker-compose.yml`

4. **Start all services:**
   ```bash
   docker-compose up -d
   ```

   This command will:
   - Download required Docker images (first time only, ~5 minutes)
   - Create PostgreSQL database container
   - Create Redis cache container
   - Build and start Backend API container
   - Build and start Frontend container

   **First-time setup takes 5-10 minutes** to download images and build containers.

5. **Verify everything is running:**
   ```bash
   docker-compose ps
   ```

   You should see all 4 services with status "Up" and "healthy":
   - `tradeanalytics_postgres`
   - `tradeanalytics_redis`
   - `tradeanalytics_backend`
   - `tradeanalytics_frontend`

6. **Access the application:**
   - **Frontend**: http://localhost:3000 (Main application)
   - **Backend API**: http://localhost:8000 (API endpoints)
   - **API Documentation**: http://localhost:8000/docs (Interactive API docs)

7. **View logs (if needed):**
   ```bash
   # View all logs
   docker-compose logs -f

   # View specific service logs
   docker logs tradeanalytics_frontend
   docker logs tradeanalytics_backend
   ```

8. **Stop the services when done:**
   ```bash
   # Stop all services (preserves data)
   docker-compose down

   # Stop and remove all data (clean slate)
   docker-compose down -v
   ```

**Troubleshooting:**
- If ports are already in use, stop other services using ports 3000, 8000, 5432, or 6379
- If containers fail to start, check logs: `docker-compose logs`
- If you get "permission denied" errors on Linux, add your user to docker group: `sudo usermod -aG docker $USER`

#### Option 2: Manual Setup (For Development)

If you want to run services individually for development:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/krabhishek8260/trade-analytics.git
   cd trade-analytics
   ```

2. **Install dependencies:**

   **Frontend:**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

   **Backend:**
   ```bash
   cd backend
   pip install -r requirements.txt
   cd ..
   ```

3. **Start required services (PostgreSQL and Redis):**
   ```bash
   # Start only database and cache services
   docker-compose up -d postgres redis
   ```

4. **Run the backend (in a new terminal):**
   ```bash
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Run the frontend (in another terminal):**
   ```bash
   cd frontend
   npm run dev
   ```

6. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Database & Authentication Setup

#### Using Docker (Recommended for Local Development)

When using Docker Compose, PostgreSQL and Redis are automatically configured. You don't need to install them separately.

**Default credentials (already configured in docker-compose.yml):**
- PostgreSQL: `postgres:postgres@localhost:5432/tradeanalytics`
- Redis: `localhost:6379`

#### Setting up Supabase (Optional - for authentication)

Supabase provides authentication and additional database features. You can:

**Option A: Skip Supabase (Use Demo Mode)**
- The app works in demo mode without Supabase
- Skip the Supabase environment variables
- Authentication will use a demo user

**Option B: Set up Supabase (For production-like setup)**

1. **Create a Supabase account** (free tier available)
   - Go to [supabase.com](https://supabase.com)
   - Create a new account
   - Create a new project

2. **Get your Supabase credentials:**
   - Go to Project Settings → API
   - Copy the `Project URL` (this is your `SUPABASE_URL`)
   - Copy the `anon public` key (this is your `SUPABASE_ANON_KEY`)

3. **Configure environment variables** (see below)

### Environment Variables Setup

This section explains how to get all the values needed for your environment files.

#### Backend Environment Variables

Create `backend/.env` with the following variables:

##### 1. Database URL (Required)

**If using Docker (recommended):**
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/tradeanalytics
```

This is already configured in `docker-compose.yml`. No setup needed!

**Format explained:**
- `postgresql://` - Database type
- `postgres:postgres` - username:password
- `@localhost:5432` - host:port
- `/tradeanalytics` - database name

##### 2. Redis URL (Required)

**Option A: Using Docker (recommended):**
```bash
REDIS_URL=redis://localhost:6379
```

This is already configured in `docker-compose.yml`. No setup needed!

**Option B: Local Redis Installation**

If you want to run Redis directly on your machine instead of Docker:

1. **Install Redis:**
   ```bash
   # macOS
   brew install redis

   # Ubuntu/Debian
   sudo apt-get install redis-server

   # Windows (via WSL or download from redis.io)
   # Or use: choco install redis-64
   ```

2. **Start Redis:**
   ```bash
   # macOS (using Homebrew)
   brew services start redis

   # Or start manually
   redis-server

   # Ubuntu/Debian
   sudo systemctl start redis-server
   ```

3. **Verify Redis is running:**
   ```bash
   redis-cli ping
   # Should return: PONG
   ```

4. **Use in your `.env`:**
   ```bash
   REDIS_URL=redis://localhost:6379
   ```

5. **Stop Redis when done:**
   ```bash
   # macOS (using Homebrew)
   brew services stop redis

   # Ubuntu/Debian
   sudo systemctl stop redis-server
   ```

**Format explained:**
- `redis://` - Protocol
- `localhost:6379` - host:port (default Redis port)

##### 3. JWT Secret (Required)

**For local development:**
```bash
JWT_SECRET=local-dev-secret-key-change-in-production
```

This can be any random string. For production, use a secure random string:
```bash
# Generate a secure secret (run this in terminal)
openssl rand -hex 32
```

##### 4. Supabase Configuration (Optional)

**Option A: Skip Supabase (Demo Mode)**

Simply don't include these variables. The app will work in demo mode.

**Option B: Local Supabase (Recommended for Development)**

Run Supabase locally using Docker. This is free and doesn't require a Supabase account.

1. **Install Supabase CLI:**
   ```bash
   # macOS/Linux
   brew install supabase/tap/supabase

   # Or via npm (all platforms)
   npm install -g supabase
   ```

2. **Initialize Supabase in your project:**
   ```bash
   # Run from project root
   supabase init
   ```

3. **Start local Supabase:**
   ```bash
   supabase start
   ```

   This will:
   - Download Supabase Docker images (~2GB first time)
   - Start PostgreSQL, Auth, Storage, and other services
   - Take 2-5 minutes on first run

4. **Get your local credentials:**

   After `supabase start` completes, you'll see output like:
   ```
   API URL: http://localhost:54321
   anon key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0
   service_role key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

   Copy these values to your `.env`:
   ```bash
   SUPABASE_URL=http://localhost:54321
   SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0
   ```

5. **Access Supabase Studio (optional):**

   Open http://localhost:54323 in your browser to access the Supabase admin dashboard.

6. **Stop local Supabase when done:**
   ```bash
   supabase stop
   ```

**Useful commands:**
```bash
supabase status    # Check if Supabase is running
supabase stop      # Stop all Supabase containers
supabase db reset  # Reset database to initial state
```

**Option C: Cloud Supabase (Production Setup)**

Use the hosted Supabase service for production or if you prefer cloud setup.

1. **Go to [supabase.com](https://supabase.com)** and sign up/login

2. **Create a new project:**
   - Click "New Project"
   - Choose your organization (or create one)
   - Enter project details:
     - **Name**: `tradeanalytics` (or any name you prefer)
     - **Database Password**: Choose a strong password (save this!)
     - **Region**: Choose closest to you
   - Click "Create new project"
   - Wait 2-3 minutes for setup to complete

3. **Get your credentials:**
   - Once project is ready, go to **Project Settings** (gear icon in sidebar)
   - Click **API** in the left menu
   - You'll see:

   **Project URL:**
   ```
   https://xxxxxxxxxxxxx.supabase.co
   ```
   Copy this as your `SUPABASE_URL`

   **anon public key:** (under "Project API keys")
   ```
   eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```
   Copy this as your `SUPABASE_ANON_KEY`

4. **Add to your `.env` file:**
   ```bash
   SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
   SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

##### Complete `backend/.env` Example

**Minimal (Docker + Demo Mode):**
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/tradeanalytics
REDIS_URL=redis://localhost:6379
JWT_SECRET=local-dev-secret-key-change-in-production
```

**Full (with Supabase):**
```bash
# Database & Cache (automatically configured by Docker)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/tradeanalytics
REDIS_URL=redis://localhost:6379

# Security
JWT_SECRET=your-generated-secret-key-here

# Supabase Authentication
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Frontend Environment Variables

Create `frontend/.env.local` with the following variables:

##### 1. Backend API URL (Required)

**For local development:**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

This tells the frontend where to find your backend API.

**Note:** The `NEXT_PUBLIC_` prefix is required for Next.js to expose this variable to the browser.

##### 2. Supabase Configuration (Optional)

**If you set up Supabase in the backend:**

Use the **same values** you got from Supabase:

```bash
NEXT_PUBLIC_SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**If you're using Demo Mode:**

Skip these variables - they're not needed.

##### Complete `frontend/.env.local` Example

**Minimal (Demo Mode):**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Full (with Supabase):**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Quick Start Configuration (Minimal Setup)

If you just want to run the app quickly without authentication:

**backend/.env** (minimal):
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/tradeanalytics
REDIS_URL=redis://localhost:6379
JWT_SECRET=local-dev-secret-key
```

**frontend/.env.local** (minimal):
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

This will run the app with:
- ✅ Local PostgreSQL database (via Docker)
- ✅ Local Redis cache (via Docker)
- ✅ Demo mode authentication (no Supabase needed)

## Development

### Backend Development

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

### Database Migrations

```bash
cd backend
alembic upgrade head
```

## Project Structure

```
tradeanalytics-v2/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── core/           # Configuration, security
│   │   ├── models/         # Pydantic models
│   │   ├── services/       # Business logic
│   │   ├── database/       # Database models
│   │   └── utils/          # Utilities
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/               # Next.js frontend
│   ├── src/
│   │   ├── app/           # App Router
│   │   ├── components/    # React components
│   │   ├── hooks/         # Custom hooks
│   │   ├── lib/           # Utilities
│   │   ├── types/         # TypeScript types
│   │   └── store/         # State management
│   ├── package.json
│   └── Dockerfile
├── database/              # Database migrations
├── docker-compose.yml     # Local development
└── README.md
```

## API Documentation

The API documentation is automatically generated and available at `/docs` when running the backend.

## Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Tests
```bash
cd frontend
npm test
```

## Troubleshooting

### Frontend Development Issues

#### Next.js Chunk Loading Errors (404 errors)
If you encounter 404 errors for static chunks like:
```
GET /_next/static/chunks/main-app.js 404
GET /_next/static/css/app/layout.css 404
```

**Quick Fix:**
```bash
cd frontend
npm run dev:clean
```

**Complete Reset:**
```bash
cd frontend
./dev-reset.sh
```

**Manual Cleanup:**
```bash
cd frontend
# Stop all Next.js processes
pkill -f "next dev" 2>/dev/null || true

# Clear all caches
rm -rf .next
rm -rf node_modules/.cache
rm -rf .turbo

# Reinstall dependencies
npm install

# Start fresh
npm run dev
```

#### Port Conflicts
If you see "Port 3000 is in use" errors:
```bash
# Find and kill processes using port 3000
lsof -ti:3000 | xargs kill -9

# Or use a different port
npm run dev -- -p 3001
```

#### Build Cache Issues
If you experience build or compilation issues:
```bash
cd frontend
# Clear all caches and node_modules
rm -rf .next node_modules package-lock.json
npm install
npm run dev
```

### Backend Development Issues

#### Database Connection Issues
```bash
cd backend
# Check database status
docker-compose ps

# Restart database
docker-compose restart postgres

# Reset database (WARNING: This will delete all data)
docker-compose down -v
docker-compose up -d
```

#### API Endpoint Issues
```bash
# Check if backend is running
curl http://localhost:8000/health

# Check API documentation
open http://localhost:8000/docs
```

#### Python Environment Issues
```bash
cd backend
# Recreate virtual environment
rm -rf venv
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Docker Issues

#### Container Won't Start
```bash
# Check container logs
docker-compose logs

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

#### Volume Issues
```bash
# Clear all volumes (WARNING: This will delete all data)
docker-compose down -v
docker volume prune -f
docker-compose up -d
```

### Common Error Solutions

#### "Module not found" errors
```bash
# Frontend
cd frontend
rm -rf node_modules package-lock.json
npm install

# Backend
cd backend
pip install -r requirements.txt
```

#### "Permission denied" errors
```bash
# Fix file permissions
chmod +x frontend/dev-reset.sh
chmod +x backend/scripts/*.sh  # if any scripts exist
```

#### "Port already in use" errors
```bash
# Find and kill processes
lsof -ti:3000 | xargs kill -9  # Frontend
lsof -ti:8000 | xargs kill -9  # Backend
```

### Development Scripts

The project includes several helpful scripts for development:

**Frontend Scripts:**
- `npm run dev` - Start development server
- `npm run dev:clean` - Clear cache and restart
- `npm run dev:fresh` - Complete reset with dependency reinstall
- `npm run dev:reset` - Reset with Turbo mode
- `./dev-reset.sh` - Complete environment reset

**Backend Scripts:**
- `uvicorn app.main:app --reload` - Start development server
- `pytest` - Run tests
- `alembic upgrade head` - Apply database migrations

### Getting Help

If you're still experiencing issues:

1. Check the logs: `docker-compose logs -f`
2. Verify environment variables are set correctly
3. Ensure all dependencies are installed
4. Try the complete reset procedures above
5. Check the [Issues](https://github.com/your-repo/issues) page for known problems

## Deployment

The application can be deployed using Docker containers or on cloud platforms like Vercel (frontend) and Railway (backend).

## License

MIT License


 A rolled options chain will have multiple orders. The first order will have a      │
│   sell to open/buy to open only. subsequent orders should have 2 legs. if the first  │
│   order was sell to open call/put then the subsequenr order should a buy to clsoe    │
│   sell/put(same sell or put) with same strike price. if the first order was buy to   │
│   open then the subsequent order should have a sell to close(same sell or put). the  │
│   last order in the chain can have just one oppsoite end. for sell to open chain     │
│   the last should be buy to close and opposite for one with first order buy to open  │
│   which should be sell to close  