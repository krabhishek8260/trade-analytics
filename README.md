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

- Docker and Docker Compose
- Node.js 18+ (for frontend development)
- Python 3.11+ (for backend development)

### Local Development

1. Clone the repository:
```bash
git clone <repository-url>
cd tradeanalytics-v2
```

2. Start the development environment:
```bash
docker-compose up -d
```

3. The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Environment Variables

Create `.env` files in both `backend/` and `frontend/` directories:

**backend/.env**:
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/tradeanalytics
REDIS_URL=redis://localhost:6379
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
JWT_SECRET=your_jwt_secret
ROBINHOOD_USERNAME=your_robinhood_username
ROBINHOOD_PASSWORD=your_robinhood_password
```

**frontend/.env.local**:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

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