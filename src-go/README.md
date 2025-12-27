# Go implementation of Antigravity Quota API

This is a Go port of the Python FastAPI server for querying Google Cloud Code AI model quotas.

## Features

- **Auto Token Refresh** - Automatically refreshes expired OAuth tokens
- **Real-time Quota Data** - Query remaining quota percentages for all models  
- **Reset Time Tracking** - Shows both absolute and relative reset times
- **Filtered Endpoints** - Dedicated endpoints for specific model families
- **Thread-safe Caching** - Concurrent-safe quota data caching

## Quick Start

### Prerequisites

- Go 1.25.5+
- Antigravity account JSON file
- `.env` file with OAuth credentials (same as Python version)

### Installation

```bash
cd src-go
go mod tidy
```

### Running the Server

```bash
cd src-go
go run .
```

The server will start at `http://0.0.0.0:8000`.

## API Endpoints

Same endpoints as the Python version:

| Endpoint | Description |
|----------|-------------|
| `GET /quota` | List all available endpoints |
| `GET /quota/usage` | Alias for `/quota` |
| `GET /quota/overview` | Quick summary string (e.g., "Pro 95% \| Flash 90% \| Claude 80%") |
| `GET /quota/status` | Terminal status with colored nerdfont icons |
| `GET /quota/all` | All Gemini and Claude models |
| `GET /quota/pro` | Gemini 3 Pro models (high, image, low) |
| `GET /quota/flash` | Gemini 3 Flash model |
| `GET /quota/claude` | Claude 4.5 models |

## Testing

```bash
cd test-go
go test -v
```

## Building

```bash
cd src-go
go build -o antigravity-quota
./antigravity-quota
```

## Configuration

Uses the same `.env` file as the Python version. The Go implementation automatically looks for the `.env` file in the parent directory.

## Differences from Python Version

- Uses Gin web framework instead of FastAPI
- Thread-safe caching with sync.RWMutex
- Native Go HTTP client instead of httpx
- Structured error handling with Go's error interface
- Static typing throughout

## Performance

The Go implementation offers:
- Lower memory usage
- Faster startup time  
- Better concurrent request handling
- Single binary deployment
