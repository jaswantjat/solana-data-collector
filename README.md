# Solana Data Collector

A comprehensive data collection and analysis tool for Solana tokens, focusing on token metrics, holder analysis, and market trends.

## Features

- Token data collection from multiple sources (Helius, Shyft, BitQuery)
- Real-time token price and volume tracking
- Holder analysis and wallet profiling
- Market trend analysis and alerts
- Performance monitoring and caching
- REST API endpoints for data access

## Tech Stack

- Python 3.10
- FastAPI
- PostgreSQL (Supabase)
- Redis (Redis Labs)
- Docker
- Render for deployment

## Prerequisites

- Python 3.10 or higher
- PostgreSQL database (Supabase)
- Redis instance (Redis Labs)
- API keys for:
  - Helius
  - Shyft
  - BitQuery

## Environment Variables

Create a `.env` file with the following variables:

```env
# Database Configuration (Supabase)
DATABASE_URL=postgres://[YOUR-SUPABASE-URL]
SUPABASE_URL=https://[YOUR-PROJECT-ID].supabase.co
SUPABASE_KEY=[YOUR-SUPABASE-ANON-KEY]

# Redis Configuration (Redis Labs)
REDIS_URL=redis://[YOUR-REDIS-LABS-URL]
REDIS_PASSWORD=[YOUR-REDIS-PASSWORD]

# API Keys
HELIUS_API_KEY=[YOUR-HELIUS-API-KEY]
SHYFT_API_KEY=[YOUR-SHYFT-API-KEY]
BITQUERY_API_KEY=[YOUR-BITQUERY-API-KEY]

# Discord Webhook (Optional)
DISCORD_WEBHOOK_URL=[YOUR-WEBHOOK-URL]
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/[YOUR-USERNAME]/solana-data-collector.git
cd solana-data-collector
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
uvicorn src.api.dashboard:app --reload
```

## API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Deployment

The application is configured for deployment on Render:

1. Fork this repository
2. Create a new Web Service on Render
3. Connect your GitHub repository
4. Set environment variables in Render dashboard
5. Deploy!

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - see LICENSE file for details
