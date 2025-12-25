# Antigravity Quota API

A FastAPI server for querying Google Cloud Code AI model quotas. Monitor your Gemini and Claude model usage through a simple REST API.

## Features

- **Auto Token Refresh** - Automatically refreshes expired OAuth tokens
- **Real-time Quota Data** - Query remaining quota percentages for all models
- **Reset Time Tracking** - Shows both absolute and relative reset times
- **Filtered Endpoints** - Dedicated endpoints for specific model families

## Quick Start

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager
- Antigravity account JSON file (exported from Antigravity app)

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd antigravity-quota

# Install dependencies
uv sync
```

### Configuration

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Edit `.env` with your credentials:

```bash
# Google OAuth credentials
CLIENT_ID=your-client-id
CLIENT_SECRET=your-client-secret

# Path to your Antigravity account JSON file
ACCOUNT_FILE=antigravity.json

# Server port (optional, default: 8000)
PORT=8000
```

3. Place your Antigravity account JSON file in the project root (or update `ACCOUNT_FILE` path).

### Running the Server

```bash
uv run python main.py
```

The server will start at `http://127.0.0.1:8000`.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /quota` | All Gemini and Claude models |
| `GET /quota/gemini-3-pro` | Gemini 3 Pro variants (high, image, low) |
| `GET /quota/gemini-3-flash` | Gemini 3 Flash model |
| `GET /quota/claude-4-5` | Claude 4.5 models |

### Example Response

```json
{
  "quota": {
    "models": [
      {
        "name": "gemini-3-pro-high",
        "percentage": 100,
        "reset_time": "2025-12-26T02:15:53Z",
        "reset_time_relative": "4h 55m"
      }
    ],
    "last_updated": 1766697635,
    "is_forbidden": false
  }
}
```

### Quick Examples

```bash
# Get all quotas
curl -s http://127.0.0.1:8000/quota | jq

# Get only low quota models (< 20%)
curl -s http://127.0.0.1:8000/quota | jq '.quota.models[] | select(.percentage < 20)'

# Get all model names
curl -s http://127.0.0.1:8000/quota | jq -r '.quota.models[].name'
```

## Interactive Docs

When the server is running:

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

## Project Structure

```
antigravity-quota/
├── main.py           # Entry point - starts the uvicorn server
├── ag_quota_api.py   # FastAPI app with all endpoints and logic
├── .env              # Environment variables (not in git)
├── .env.example      # Example environment file
├── API.md            # Detailed API documentation
└── README.md         # This file
```

## How It Works

1. **Token Management**: Reads OAuth tokens from your Antigravity account JSON file and automatically refreshes them when expired (5-minute buffer).

2. **Quota Fetching**: Uses Google's CloudCode internal API to fetch available models and their quota information.

3. **Data Formatting**: Converts raw API responses to a clean format with percentage values and human-readable reset times.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CLIENT_ID` | Yes | - | Google OAuth Client ID |
| `CLIENT_SECRET` | Yes | - | Google OAuth Client Secret |
| `ACCOUNT_FILE` | No | `antigravity.json` | Path to account JSON file |
| `PORT` | No | `8000` | Server port |

## Docker

### Build

```bash
docker build -t antigravity-quota .
```

### Run

```bash
docker run -d -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/antigravity.json:/app/antigravity.json:ro \
  --name antigravity-quota \
  antigravity-quota
```

### Docker Compose

Create a `docker-compose.yml`:

```yaml
services:
  api:
    build: .
    ports:
      - "${PORT:-8000}:8000"
    env_file:
      - .env
    volumes:
      - ./antigravity.json:/app/antigravity.json:ro
    restart: unless-stopped
```

Then run:

```bash
docker compose up -d
```

## License

MIT
