"""Z.ai/ZHIPU API client with caching."""

import logging
import os
import threading
import time
from datetime import UTC, datetime
from urllib.parse import quote, urlparse

import httpx
from cachetools import TTLCache
from fastapi import HTTPException

from .config import QUERY_DEBOUNCE

logger = logging.getLogger(__name__)

# Cache for z.ai queries
SECONDS_PER_MINUTE = 60
_zai_cache: TTLCache = TTLCache(maxsize=10, ttl=QUERY_DEBOUNCE * SECONDS_PER_MINUTE)
_zai_cache_lock = threading.Lock()


async def query_zai_endpoint(url: str, auth_token: str, query_params: str = "") -> dict:
    """Query a Z.ai API endpoint and return JSON response with caching."""
    cache_key = f"{url}{query_params}"

    # Check cache first
    with _zai_cache_lock:
        if cache_key in _zai_cache:
            logger.info("Returning cached z.ai data")
            return _zai_cache[cache_key]

    headers = {
        "Authorization": auth_token,
        "Accept-Language": "en-US,en",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url + query_params, headers=headers, timeout=10.0)
            response.raise_for_status()
            json_data = response.json()
            result = json_data.get("data", json_data)

            # Cache the result
            with _zai_cache_lock:
                _zai_cache[cache_key] = result
            logger.info("Cached z.ai data for %d minute(s)", QUERY_DEBOUNCE)

            return result
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Z.ai API error: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to query Z.ai API: {e!s}")


def get_base_domain(base_url: str) -> tuple[str, str]:
    """Extract platform and base domain from ANTHROPIC_BASE_URL."""
    if "api.z.ai" in base_url:
        return "ZAI", "https://api.z.ai"
    elif "open.bigmodel.cn" in base_url or "dev.bigmodel.cn" in base_url:
        parsed = urlparse(base_url)
        return "ZHIPU", f"{parsed.scheme}://{parsed.netloc}"
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unrecognized ANTHROPIC_BASE_URL: {base_url}. "
            "Supported: https://api.z.ai/api/anthropic or https://open.bigmodel.cn/api/anthropic",
        )


def build_time_query_params() -> str:
    """Build query parameters for time-based endpoints."""
    now = datetime.now(UTC)
    start_date = datetime(now.year, now.month, now.day - 1, now.hour, 0, 0, 0, tzinfo=UTC)
    end_date = datetime(now.year, now.month, now.day, now.hour, 59, 59, 999999, tzinfo=UTC)

    start_time = start_date.strftime("%Y-%m-%d %H:%M:%S")
    end_time = end_date.strftime("%Y-%m-%d %H:%M:%S")

    return f"?startTime={quote(start_time)}&endTime={quote(end_time)}"


def process_quota_limit(data: dict) -> dict:
    """Process quota limit data to transform type names."""
    if not data or "limits" not in data:
        return data

    limits = []
    for item in data.get("limits", []):
        if item.get("type") == "TOKENS_LIMIT":
            limits.append({"type": "Token usage(5 Hour)", "percentage": item.get("percentage")})
        elif item.get("type") == "TIME_LIMIT":
            limits.append(
                {
                    "type": "MCP usage(1 Month)",
                    "percentage": item.get("percentage"),
                    "currentUsage": item.get("currentValue"),
                    "total": item.get("usage"),
                    "usageDetails": item.get("usageDetails"),
                }
            )
        else:
            limits.append(item)

    return {**data, "limits": limits}


def format_glm_quota(quota_limit_data: dict) -> dict:
    """Format GLM quota limit data to match antigravity quota format."""
    models = []

    if not quota_limit_data or "limits" not in quota_limit_data:
        return {
            "models": models,
            "last_updated": int(time.time()),
            "is_forbidden": False,
        }

    for limit in quota_limit_data.get("limits", []):
        limit_type = limit.get("type", "")
        percentage = limit.get("percentage", 0)

        if limit_type == "Token usage(5 Hour)":
            # Token limit: show remaining percentage (100 - used)
            models.append({"name": "glm", "percentage": 100 - percentage})
        elif limit_type == "MCP usage(1 Month)":
            # MCP limit: show remaining percentage
            total = limit.get("total", 100)
            usage_details = limit.get("usageDetails", [])

            # Add overall MCP quota
            models.append({"name": "glm-coding-plan-mcp-monthly", "percentage": 100 - percentage})

            # Add individual tool usage details (excluding zread)
            for detail in usage_details:
                model_code = detail.get("modelCode", "")
                usage = detail.get("usage", 0)

                # Skip zread
                if model_code == "zread":
                    continue

                tool_percentage = int(usage / total * 100) if total > 0 else 0
                models.append({"name": f"glm-coding-plan-{model_code}", "percentage": 100 - tool_percentage})

    return {
        "models": models,
        "last_updated": int(time.time()),
        "is_forbidden": False,
    }


async def get_glm_quota() -> dict:
    """Get GLM quota data from Z.ai/ZHIPU API."""
    # Read environment variables
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
    auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")

    if not auth_token:
        raise HTTPException(status_code=400, detail="ANTHROPIC_AUTH_TOKEN environment variable is not set")

    if not base_url:
        raise HTTPException(
            status_code=400,
            detail="ANTHROPIC_BASE_URL environment variable is not set. "
            "Set it to https://api.z.ai/api/anthropic or https://open.bigmodel.cn/api/anthropic",
        )

    # Get platform and base domain
    _, base_domain = get_base_domain(base_url)

    # Query quota limit endpoint
    quota_limit_url = f"{base_domain}/api/monitor/usage/quota/limit"
    quota_limit_raw = await query_zai_endpoint(quota_limit_url, auth_token)
    quota_limit_processed = process_quota_limit(quota_limit_raw)

    # Format to match antigravity quota format
    return format_glm_quota(quota_limit_processed)
