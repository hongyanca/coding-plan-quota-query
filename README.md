# Antigravity Quota API

A FastAPI server for querying Google Cloud Code AI model quotas. Monitor your Gemini and Claude model usage through a simple REST API.

## Features

- **Auto Token Refresh** - Automatically refreshes expired OAuth tokens
- **Real-time Quota Data** - Query remaining quota percentages for all models
- **Reset Time Tracking** - Shows both absolute and relative reset times
- **Filtered Endpoints** - Dedicated endpoints for specific model families

## Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager
- Antigravity account JSON file

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
# https://github.com/lbjlaq/Antigravity-Manager/blob/main/src-tauri/src/modules/oauth.rs
CLIENT_ID=your-client-id
CLIENT_SECRET=your-client-secret

# Path to your Antigravity account JSON file
ACCOUNT_FILE=antigravity.json

# Server port (optional, default: 8000)
PORT=8000
```

3. Place your Antigravity account JSON file in the project root (or update `ACCOUNT_FILE` path). https://github.com/router-for-me/CLIProxyAPI https://help.router-for.me/configuration/provider/antigravity.html can get the `.json` file for authentication.

### Running the Server

```bash
uv run python main.py
```

The server will start at `http://0.0.0.0:8000`.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /quota` | List all available endpoints |
| `GET /quota/usage` | Alias for `/quota` |
| `GET /quota/overview` | Quick summary string (e.g., "Pro 95% \| Flash 90% \| Claude 80%") |
| `GET /quota/all` | All Gemini and Claude models |
| `GET /quota/pro` | Gemini 3 Pro models (high, image, low) |
| `GET /quota/flash` | Gemini 3 Flash model |
| `GET /quota/claude` | Claude 4.5 models |

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
├── antigravity.json           # Account file (not in git)
├── main.py                    # Entry point - starts the uvicorn server
├── src/
│   ├── __init__.py            # Package init
│   ├── api.py                 # FastAPI app and endpoints
│   ├── cloudcode_client.py    # Google Cloud Code API client
│   └── config.py              # Configuration and env loading
├── test/
│   ├── __init__.py            # Test package init
│   ├── test_api.py            # API module tests
│   └── test_cloudcode_client.py  # Client module tests
├── .env                       # Environment variables (not in git)
├── .env.example               # Example environment file
├── Dockerfile                 # Container build
├── API.md                     # Detailed API documentation
└── README.md                  # This file
```

## Testing

Run tests with pytest:

```bash
uv run pytest test/ -v
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
| `USER_AGENT` | No | `antigravity/1.13.3 Darwin/arm64` | HTTP User-Agent header |
| `QUERY_DEBOUNCE` | No | `1` | Cache duration in minutes for googleapis queries |

## Docker

### Build

```bash
docker build -t antigravity-quota .
```

### Run

```bash
docker run -d -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/antigravity.json:/app/antigravity.json \
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
      - ./antigravity.json:/app/antigravity.json
    restart: unless-stopped
```

Then run:

```bash
docker compose up -d
```

## License

MIT
