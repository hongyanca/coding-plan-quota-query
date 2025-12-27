"""Google Cloud Code API client for quota queries."""

import json
import logging
import threading
import time
from datetime import datetime

import httpx
from cachetools import TTLCache

from .config import (
    ACCOUNT_FILE,
    API_URL,
    CLIENT_ID,
    CLIENT_SECRET,
    PROJECT_API_URL,
    QUERY_DEBOUNCE,
    TOKEN_URL,
    USER_AGENT,
)
from .constants import SECONDS_PER_MINUTE, TOKEN_REFRESH_BUFFER_SECONDS

logger = logging.getLogger(__name__)


def load_account() -> dict:
    """Load account from file."""
    if not ACCOUNT_FILE.exists():
        raise FileNotFoundError(f"Account file not found: {ACCOUNT_FILE}")
    with open(ACCOUNT_FILE) as f:
        return json.load(f)


def normalize_account(account: dict) -> tuple[str, str, int | None, str | None]:
    """Normalize different account formats to extract token info."""
    if "token" in account:
        token_data = account["token"]
        return (
            token_data.get("access_token"),
            token_data.get("refresh_token"),
            token_data.get("expiry_timestamp"),
            token_data.get("project_id"),
        )

    access_token = account.get("access_token")
    refresh_token = account.get("refresh_token")
    project_id = account.get("project_id")

    expiry_timestamp = None
    if "timestamp" in account:
        timestamp_ms = account.get("timestamp")
        if timestamp_ms:
            expires_in = account.get("expires_in", 3600)
            expiry_timestamp = (timestamp_ms // 1000) + expires_in
    elif "expiry_timestamp" in account:
        expiry_timestamp = account.get("expiry_timestamp")

    return access_token, refresh_token, expiry_timestamp, project_id


def refresh_access_token(refresh_token: str) -> dict:
    """Refresh access token using refresh_token."""
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    response = httpx.post(TOKEN_URL, data=data)
    response.raise_for_status()
    return response.json()


def ensure_fresh_token(account: dict) -> str:
    """Check token expiry and refresh if needed (within 5 minutes)."""
    access_token, refresh_token, expiry_timestamp, _ = normalize_account(account)

    if not access_token or not refresh_token:
        raise ValueError("Missing access_token or refresh_token")

    now = int(time.time())
    if expiry_timestamp and expiry_timestamp > now + TOKEN_REFRESH_BUFFER_SECONDS:
        logger.info("Token is fresh, no need to refresh")
        return access_token

    # Token needs refresh
    logger.info("Token needs refresh")
    new_token_data = refresh_access_token(refresh_token)
    new_expiry = now + new_token_data["expires_in"]

    # Update account dict
    if "token" in account:
        token_data = account["token"]
        token_data["access_token"] = new_token_data["access_token"]
        token_data["expires_in"] = new_token_data["expires_in"]
        token_data["expiry_timestamp"] = new_expiry
        token_data["token_type"] = new_token_data.get("token_type", "Bearer")
    else:
        account["access_token"] = new_token_data["access_token"]
        account["expires_in"] = new_token_data["expires_in"]
        account["timestamp"] = now * 1000
        account["type"] = "antigravity"

    # Update top-level access_token and expired fields
    # expired is ISO 8601 datetime with local timezone
    expiry_dt = datetime.fromtimestamp(new_expiry).astimezone()
    account["access_token"] = new_token_data["access_token"]
    account["expired"] = expiry_dt.isoformat()

    # Write updated account back to file
    try:
        with open(ACCOUNT_FILE, "w") as f:
            json.dump(account, f, indent=2)
        logger.info("Access token refreshed, expires at %s", expiry_dt.isoformat())
    except (IOError, OSError) as e:
        logger.error("Failed to save refreshed token to %s: %s", ACCOUNT_FILE, e)

    return new_token_data["access_token"]


def get_project_id(access_token: str) -> str | None:
    """Fetch the project ID from the CloudCode API."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json",
    }
    payload = {"metadata": {"ideType": "ANTIGRAVITY"}}

    try:
        response = httpx.post(PROJECT_API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            return data.get("cloudaicompanionProject")
        logger.warning("Failed to get project ID: HTTP %d", response.status_code)
    except httpx.RequestError as e:
        logger.warning("Failed to get project ID: %s", e)

    return None


# Thread-safe cache for quota data
# TTL is set dynamically based on QUERY_DEBOUNCE config
_quota_cache: TTLCache = TTLCache(maxsize=1, ttl=QUERY_DEBOUNCE * SECONDS_PER_MINUTE)
_quota_cache_lock = threading.Lock()


def get_quota(access_token: str, project_id: str | None = None) -> dict:
    """Fetch quota information from the CloudCode API with caching."""
    cache_key = "quota"

    # Thread-safe cache check
    with _quota_cache_lock:
        if cache_key in _quota_cache:
            logger.info("Returning cached quota data")
            return _quota_cache[cache_key]

    # Fetch fresh data from API
    logger.info("Fetching fresh quota data from googleapis.com")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json",
    }
    payload = {}
    if project_id:
        payload["project"] = project_id

    response = httpx.post(API_URL, headers=headers, json=payload)
    response.raise_for_status()
    result = response.json()

    # Thread-safe cache update
    with _quota_cache_lock:
        _quota_cache[cache_key] = result
    logger.info("Cached quota data for %d minute(s)", QUERY_DEBOUNCE)

    return result
