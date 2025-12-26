# Antigravity Quota API

FastAPI server for querying Google Cloud Code AI model quotas.

## Base URL

```
http://127.0.0.1:8000
```

> **Note**: Port is configurable via `PORT` environment variable in `.env` file.

## Running the Server

```bash
# Using uv (recommended)
uv run python main.py

# Using uvicorn directly
uv run uvicorn src.api:app --reload

# Custom host/port
uv run uvicorn src.api:app --host 0.0.0.0 --port 8080
```

## Configuration

All configuration is done via environment variables in a `.env` file:

```bash
# Copy the example file
cp .env.example .env
```

| Variable | Description | Default |
|----------|-------------|---------|
| `CLIENT_ID` | Google OAuth Client ID | (required) |
| `CLIENT_SECRET` | Google OAuth Client Secret | (required) |
| `ACCOUNT_FILE` | Path to account JSON file | `antigravity.json` |
| `PORT` | Server port | `8000` |
| `USER_AGENT` | HTTP User-Agent header | `antigravity/1.13.3 Darwin/arm64` |

---

## Endpoints

### 1. List Available Endpoints

Get a list of all available quota API endpoints.

```http
GET /quota
GET /quota/usage
```

> **Note**: `/quota/usage` is an alias for `/quota`.

**Response:**

```json
{
  "message": "Welcome to the Antigravity Quota API",
  "endpoints": {
    "/quota": "This endpoint - lists all available endpoints",
    "/quota/overview": "Quick summary (e.g., 'Pro 95% | Flash 90% | Claude 80%')",
    "/quota/all": "All models with percentage and relative reset time",
    "/quota/pro": "Gemini 3 Pro models (high, image, low)",
    "/quota/flash": "Gemini 3 Flash model",
    "/quota/claude": "Claude 4.5 models (opus, sonnet, thinking)"
  }
}
```

**Example:**

```bash
curl http://127.0.0.1:8000/quota
```

---

### 2. Get Quota Overview

Get a quick summary of quota percentages.

```http
GET /quota/overview
```

**Response:**

```json
{
  "overview": "Pro 100% | Flash 100% | Claude 81%"
}
```

**Example:**

```bash
curl http://127.0.0.1:8000/quota/overview
```

---

### 3. Get All Models

Get quota information for all Gemini and Claude models.

```http
GET /quota/all
```

**Response:**

```json
{
  "quota": {
    "models": [
      {
        "name": "claude-opus-4-5-thinking",
        "percentage": 81,
        "reset_time": "2025-12-26T07:15:53Z",
        "reset_time_relative": "2h 31m"
      },
      {
        "name": "claude-sonnet-4-5",
        "percentage": 81,
        "reset_time": "2025-12-26T07:15:53Z",
        "reset_time_relative": "2h 31m"
      },
      {
        "name": "claude-sonnet-4-5-thinking",
        "percentage": 81,
        "reset_time": "2025-12-26T07:15:53Z",
        "reset_time_relative": "2h 31m"
      },
      {
        "name": "gemini-2.5-flash",
        "percentage": 99,
        "reset_time": "2025-12-26T09:27:46Z",
        "reset_time_relative": "4h 43m"
      },
      {
        "name": "gemini-2.5-flash-lite",
        "percentage": 99,
        "reset_time": "2025-12-26T09:39:31Z",
        "reset_time_relative": "4h 54m"
      },
      {
        "name": "gemini-2.5-flash-thinking",
        "percentage": 99,
        "reset_time": "2025-12-26T09:27:46Z",
        "reset_time_relative": "4h 43m"
      },
      {
        "name": "gemini-2.5-pro",
        "percentage": 100,
        "reset_time": "2025-12-26T09:44:43Z",
        "reset_time_relative": "4h 59m"
      },
      {
        "name": "gemini-3-flash",
        "percentage": 100,
        "reset_time": "2025-12-26T09:44:43Z",
        "reset_time_relative": "4h 59m"
      },
      {
        "name": "gemini-3-pro-high",
        "percentage": 100,
        "reset_time": "2025-12-26T09:44:43Z",
        "reset_time_relative": "4h 59m"
      },
      {
        "name": "gemini-3-pro-image",
        "percentage": 100,
        "reset_time": "2025-12-26T09:44:43Z",
        "reset_time_relative": "4h 59m"
      },
      {
        "name": "gemini-3-pro-low",
        "percentage": 100,
        "reset_time": "2025-12-26T09:44:43Z",
        "reset_time_relative": "4h 59m"
      }
    ],
    "last_updated": 1766724284,
    "is_forbidden": false
  }
}
```

**Example:**

```bash
curl http://127.0.0.1:8000/quota/all | jq '.quota.models[].name'
```

---

### 4. Get Gemini 3 Pro Models

Get quota for Gemini 3 Pro variants (high, image, low).

```http
GET /quota/pro
```

**Response:**

```json
{
  "quota": {
    "models": [
      {
        "name": "gemini-3-pro-high",
        "percentage": 100,
        "reset_time": "2025-12-26T09:44:43Z",
        "reset_time_relative": "4h 59m"
      },
      {
        "name": "gemini-3-pro-image",
        "percentage": 100,
        "reset_time": "2025-12-26T09:44:43Z",
        "reset_time_relative": "4h 59m"
      },
      {
        "name": "gemini-3-pro-low",
        "percentage": 100,
        "reset_time": "2025-12-26T09:44:43Z",
        "reset_time_relative": "4h 59m"
      }
    ],
    "last_updated": 1766724285,
    "is_forbidden": false
  }
}
```

**Example:**

```bash
curl http://127.0.0.1:8000/quota/pro | jq '.quota.models[] | {name, percentage}'
```

---

### 5. Get Gemini 3 Flash Model

Get quota for Gemini 3 Flash model.

```http
GET /quota/flash
```

**Response:**

```json
{
  "quota": {
    "models": [
      {
        "name": "gemini-3-flash",
        "percentage": 100,
        "reset_time": "2025-12-26T09:44:43Z",
        "reset_time_relative": "4h 59m"
      }
    ],
    "last_updated": 1766724286,
    "is_forbidden": false
  }
}
```

**Example:**

```bash
curl http://127.0.0.1:8000/quota/flash | jq '.quota.models[0]'
```

---

### 6. Get Claude 4.5 Models

Get quota for Claude 4.5 models.

```http
GET /quota/claude
```

**Response:**

```json
{
  "quota": {
    "models": [
      {
        "name": "claude-opus-4-5-thinking",
        "percentage": 81,
        "reset_time": "2025-12-26T07:15:53Z",
        "reset_time_relative": "2h 31m"
      },
      {
        "name": "claude-sonnet-4-5",
        "percentage": 81,
        "reset_time": "2025-12-26T07:15:53Z",
        "reset_time_relative": "2h 31m"
      },
      {
        "name": "claude-sonnet-4-5-thinking",
        "percentage": 81,
        "reset_time": "2025-12-26T07:15:53Z",
        "reset_time_relative": "2h 31m"
      }
    ],
    "last_updated": 1766724287,
    "is_forbidden": false
  }
}
```

**Example:**

```bash
curl http://127.0.0.1:8000/quota/claude | jq '.quota.models[] | select(.percentage < 100)'
```

---

## Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Model identifier |
| `percentage` | integer | Remaining quota percentage (0-100) |
| `reset_time` | string | ISO 8601 timestamp when quota resets |
| `reset_time_relative` | string | Human-readable time until reset (e.g., "4h 35m") |
| `last_updated` | integer | Unix timestamp of when quota was fetched |
| `is_forbidden` | boolean | Whether the account is forbidden (403 error) |

---

## Interactive API Docs

When the server is running, visit:

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

---

## Common Queries

### Get quick overview
```bash
curl -s http://127.0.0.1:8000/quota/overview | jq -r '.overview'
```

### Get low quota models (< 20%)
```bash
curl -s http://127.0.0.1:8000/quota/all | jq '.quota.models[] | select(.percentage < 20)'
```

### Get models expiring soon (< 1 hour)
```bash
curl -s http://127.0.0.1:8000/quota/all | jq '.quota.models[] | select(.reset_time_relative | contains("0h"))'
```

### Get percentage for specific model
```bash
curl -s http://127.0.0.1:8000/quota/all | jq '.quota.models[] | select(.name == "gemini-3-pro-high") | .percentage'
```

### Get all model names
```bash
curl -s http://127.0.0.1:8000/quota/all | jq -r '.quota.models[].name'
```
