# Trading Research App

A comprehensive research-focused trading platform with multi-agent AI analysis for tracking investments and generating research recommendations.

## Features

- **AI-Powered Research**: Multi-agent system using LangGraph for fundamental, technical, and sentiment analysis
- **Portfolio Tracking**: Log and track confirmed trades with real-time valuations
- **Analytics Dashboard**: Performance metrics, allocation breakdowns, and benchmark comparisons
- **Robinhood Integration**: Recommendations filtered to Robinhood-tradable assets
- **Backtesting**: Test strategies including MACD, SMA crossover, RSI, momentum, and mean reversion

## Important Notice

**This application is for research and educational purposes only.**

- Does NOT provide financial advice
- Does NOT execute trades on your behalf
- All recommendations are informational only
- You must manually execute trades through Robinhood or your preferred broker

## Tech Stack

### Backend
- FastAPI (Python 3.10+)
- SQLAlchemy with SQLite/PostgreSQL
- LangGraph for agent orchestration
- yfinance for market data

### Frontend
- Next.js 14 with TypeScript
- ShadcnUI components
- Tailwind CSS
- Recharts for visualizations

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 20+
- (Optional) Docker and Docker Compose

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp ../.env.example .env
# Edit .env with your API keys

# Run the server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

The frontend will be available at http://localhost:3000

### Using Docker

```bash
# Copy environment file
cp .env.example .env
# Edit .env with your configuration

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | JWT signing key | Yes |
| `DATABASE_URL` | Database connection string | Yes |
| `LLM_PROVIDER` | `openai` or `anthropic` | Yes |
| `OPENAI_API_KEY` | OpenAI API key | If using OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic API key | If using Anthropic |

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

- `POST /api/auth/register` - Create new account
- `POST /api/auth/login` - Login and get token
- `POST /api/research/generate-sync` - Generate research report
- `POST /api/trades/confirm` - Log a confirmed trade
- `GET /api/analytics/portfolio` - Get portfolio summary

## Project Structure

```
trading-research-app/
├── frontend/               # Next.js application
│   ├── app/               # App router pages
│   ├── components/        # React components
│   └── lib/               # Utilities and API client
│
├── backend/               # FastAPI application
│   └── app/
│       ├── routers/       # API endpoints
│       ├── agents/        # LangGraph agents
│       ├── services/      # Business logic
│       └── strategies/    # Trading strategies
│
├── docker-compose.yml     # Docker orchestration
└── .github/workflows/     # CI/CD pipeline
```

## Deployment

### Vercel (Frontend)

1. Connect your GitHub repository to Vercel
2. Set the root directory to `frontend`
3. Add environment variable: `NEXT_PUBLIC_API_URL`

### Render (Backend)

1. Connect your GitHub repository to Render
2. Use the included `render.yaml` blueprint
3. Add your API keys as environment variables

## License

MIT License - see LICENSE file for details.

## Disclaimer

This software is provided "as is" without warranty of any kind. The authors are not responsible for any financial losses incurred from using this software. Always do your own research and consult with a qualified financial advisor before making investment decisions.
