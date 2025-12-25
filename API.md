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
uv run uvicorn ag_quota_api:app --reload

# Custom host/port
uv run uvicorn ag_quota_api:app --host 0.0.0.0 --port 8080
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

---

## Endpoints

### 1. Get All Models

Get quota information for all Gemini and Claude models.

```http
GET /quota
```

**Response:**

```json
{
  "quota": {
    "models": [
      {
        "name": "claude-opus-4-5-thinking",
        "percentage": 99,
        "reset_time": "2025-12-25T15:13:37Z",
        "reset_time_relative": "4h 28m"
      },
      {
        "name": "claude-sonnet-4-5",
        "percentage": 99,
        "reset_time": "2025-12-25T15:13:37Z",
        "reset_time_relative": "4h 28m"
      },
      {
        "name": "claude-sonnet-4-5-thinking",
        "percentage": 99,
        "reset_time": "2025-12-25T15:13:37Z",
        "reset_time_relative": "4h 28m"
      },
      {
        "name": "gemini-2.5-flash",
        "percentage": 100,
        "reset_time": "2025-12-25T15:21:27Z",
        "reset_time_relative": "4h 35m"
      },
      {
        "name": "gemini-2.5-flash-lite",
        "percentage": 100,
        "reset_time": "2025-12-25T15:21:27Z",
        "reset_time_relative": "4h 35m"
      },
      {
        "name": "gemini-2.5-flash-thinking",
        "percentage": 100,
        "reset_time": "2025-12-25T15:21:27Z",
        "reset_time_relative": "4h 35m"
      },
      {
        "name": "gemini-2.5-pro",
        "percentage": 100,
        "reset_time": "2025-12-25T15:21:27Z",
        "reset_time_relative": "4h 35m"
      },
      {
        "name": "gemini-3-flash",
        "percentage": 100,
        "reset_time": "2025-12-25T15:21:27Z",
        "reset_time_relative": "4h 35m"
      },
      {
        "name": "gemini-3-pro-high",
        "percentage": 100,
        "reset_time": "2025-12-25T15:21:27Z",
        "reset_time_relative": "4h 35m"
      },
      {
        "name": "gemini-3-pro-image",
        "percentage": 100,
        "reset_time": "2025-12-25T15:21:27Z",
        "reset_time_relative": "4h 35m"
      },
      {
        "name": "gemini-3-pro-low",
        "percentage": 100,
        "reset_time": "2025-12-25T15:21:27Z",
        "reset_time_relative": "4h 35m"
      }
    ],
    "last_updated": 1766658087,
    "is_forbidden": false
  }
}
```

**Example:**

```bash
curl http://127.0.0.1:8000/quota | jq '.quota.models[].name'
```

---

### 2. Get Gemini 3 Pro Models

Get quota for Gemini 3 Pro variants (high, image, low).

```http
GET /quota/gemini-3-pro
```

**Response:**

```json
{
  "quota": {
    "models": [
      {
        "name": "gemini-3-pro-high",
        "percentage": 100,
        "reset_time": "2025-12-25T15:21:27Z",
        "reset_time_relative": "4h 35m"
      },
      {
        "name": "gemini-3-pro-image",
        "percentage": 100,
        "reset_time": "2025-12-25T15:21:27Z",
        "reset_time_relative": "4h 35m"
      },
      {
        "name": "gemini-3-pro-low",
        "percentage": 100,
        "reset_time": "2025-12-25T15:21:27Z",
        "reset_time_relative": "4h 35m"
      }
    ],
    "last_updated": 1766658087,
    "is_forbidden": false
  }
}
```

**Example:**

```bash
curl http://127.0.0.1:8000/quota/gemini-3-pro | jq '.quota.models[] | {name, percentage, reset_time_relative}'
```

---

### 3. Get Gemini 3 Flash Model

Get quota for Gemini 3 Flash model.

```http
GET /quota/gemini-3-flash
```

**Response:**

```json
{
  "quota": {
    "models": [
      {
        "name": "gemini-3-flash",
        "percentage": 100,
        "reset_time": "2025-12-25T15:21:27Z",
        "reset_time_relative": "4h 35m"
      }
    ],
    "last_updated": 1766658087,
    "is_forbidden": false
  }
}
```

**Example:**

```bash
curl http://127.0.0.1:8000/quota/gemini-3-flash | jq '.quota.models[0]'
```

---

### 4. Get Claude 4.5 Models

Get quota for Claude 4.5 models.

```http
GET /quota/claude-4-5
```

**Response:**

```json
{
  "quota": {
    "models": [
      {
        "name": "claude-opus-4-5-thinking",
        "percentage": 99,
        "reset_time": "2025-12-25T15:13:37Z",
        "reset_time_relative": "4h 28m"
      },
      {
        "name": "claude-sonnet-4-5",
        "percentage": 99,
        "reset_time": "2025-12-25T15:13:37Z",
        "reset_time_relative": "4h 28m"
      },
      {
        "name": "claude-sonnet-4-5-thinking",
        "percentage": 99,
        "reset_time": "2025-12-25T15:13:37Z",
        "reset_time_relative": "4h 28m"
      }
    ],
    "last_updated": 1766658087,
    "is_forbidden": false
  }
}
```

**Example:**

```bash
curl http://127.0.0.1:8000/quota/claude-4-5 | jq '.quota.models[] | select(.percentage < 100)'
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

### Get low quota models (< 20%)
```bash
curl -s http://127.0.0.1:8000/quota | jq '.quota.models[] | select(.percentage < 20)'
```

### Get models expiring soon (< 1 hour)
```bash
curl -s http://127.0.0.1:8000/quota | jq '.quota.models[] | select(.reset_time_relative | contains("0h"))'
```

### Get percentage for specific model
```bash
curl -s http://127.0.0.1:8000/quota | jq '.quota.models[] | select(.name == "gemini-3-pro-high") | .percentage'
```

### Get all model names
```bash
curl -s http://127.0.0.1:8000/quota | jq -r '.quota.models[].name'
```
