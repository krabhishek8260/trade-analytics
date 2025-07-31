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