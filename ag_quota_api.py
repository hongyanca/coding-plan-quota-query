#!/usr/bin/env python3
"""
FastAPI server for Antigravity quota queries.

Endpoints:
- GET /quota - All models with relative reset time
- GET /quota/gemini-3-pro - Gemini 3 Pro models (high, image, low)
- GET /quota/gemini-3-flash - Gemini 3 Flash model
- GET /quota/claude-4-5 - Claude 4.5 models
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

# Load environment variables from .env file
load_dotenv()

API_URL = "https://cloudcode-pa.googleapis.com/v1internal:fetchAvailableModels"
PROJECT_API_URL = "https://cloudcode-pa.googleapis.com/v1internal:loadCodeAssist"
TOKEN_URL = "https://oauth2.googleapis.com/token"

# User agent (loaded from .env)
USER_AGENT = os.getenv("USER_AGENT", "antigravity/1.13.3 Darwin/arm64")

# Google OAuth credentials (loaded from .env)
# https://github.com/lbjlaq/Antigravity-Manager/blob/main/src-tauri/src/modules/oauth.rs)
CLIENT_ID = os.getenv("CLIENT_ID", "")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")

# Account file path (loaded from .env)
ACCOUNT_FILE = Path(os.getenv("ACCOUNT_FILE", "antigravity.json"))

app = FastAPI(title="Antigravity Quota API")


def load_account() -> dict:
    """Load account from file."""
    if not ACCOUNT_FILE.exists():
        raise HTTPException(status_code=500, detail=f"Account file not found: {ACCOUNT_FILE}")
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
        raise HTTPException(status_code=500, detail="Missing access_token or refresh_token")

    now = int(time.time())
    if expiry_timestamp and expiry_timestamp > now + 300:
        return access_token

    # Token needs refresh
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
    account["access_token"] = new_token_data["access_token"]
    account["expired"] = new_expiry

    # Write updated account back to file
    try:
        with open(ACCOUNT_FILE, "w") as f:
            json.dump(account, f, indent=2)
    except Exception:
        pass  # Silently fail if can't save

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
    except Exception:
        pass

    return None


def get_quota(access_token: str, project_id: str | None = None) -> dict:
    """Fetch quota information from the CloudCode API."""
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
    return response.json()


def format_time_remaining(reset_time: str) -> str:
    """Calculate time remaining until reset in 'Xh Ym' format."""
    try:
        reset_dt = datetime.fromisoformat(reset_time.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = reset_dt - now

        if delta.total_seconds() <= 0:
            return "Reset due"

        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        return f"{hours}h {minutes}m"
    except:
        return ""


def format_quota(quota_data: dict, show_relative: bool = True) -> dict:
    """Format quota data to match antigravity-mgr account format."""
    models = quota_data.get("models", {})
    model_list = []

    for name, info in models.items():
        quota_info = info.get("quotaInfo", {})
        remaining_fraction = quota_info.get("remainingFraction")
        reset_time = quota_info.get("resetTime")

        if remaining_fraction is not None:
            name_lower = name.lower()
            if "gemini" in name_lower or "claude" in name_lower:
                model_entry = {
                    "name": name,
                    "percentage": int(remaining_fraction * 100),
                    "reset_time": reset_time,
                }
                if show_relative and reset_time:
                    model_entry["reset_time_relative"] = format_time_remaining(reset_time)
                model_list.append(model_entry)

    return {
        "models": sorted(model_list, key=lambda m: m["name"]),
        "last_updated": int(time.time()),
        "is_forbidden": False,
    }


def filter_models(quota: dict, patterns: list[str]) -> dict:
    """Filter models by name patterns."""
    filtered = [m for m in quota["models"] if any(p in m["name"].lower() for p in patterns)]
    return {
        "models": filtered,
        "last_updated": quota["last_updated"],
        "is_forbidden": quota["is_forbidden"],
    }


@app.get("/quota")
async def get_all_quota():
    """Get all models with relative reset time."""
    account = load_account()
    access_token = ensure_fresh_token(account)
    _, _, _, project_id = normalize_account(account)

    if not project_id:
        project_id = get_project_id(access_token)

    quota_raw = get_quota(access_token, project_id)
    return {"quota": format_quota(quota_raw, show_relative=True)}


@app.get("/quota/gemini-3-pro")
async def get_gemini_3_pro():
    """Get Gemini 3 Pro models (high, image, low)."""
    account = load_account()
    access_token = ensure_fresh_token(account)
    _, _, _, project_id = normalize_account(account)

    if not project_id:
        project_id = get_project_id(access_token)

    quota_raw = get_quota(access_token, project_id)
    quota_formatted = format_quota(quota_raw, show_relative=True)
    filtered = filter_models(quota_formatted, ["gemini-3-pro-high", "gemini-3-pro-image", "gemini-3-pro-low"])
    return {"quota": filtered}


@app.get("/quota/gemini-3-flash")
async def get_gemini_3_flash():
    """Get Gemini 3 Flash model."""
    account = load_account()
    access_token = ensure_fresh_token(account)
    _, _, _, project_id = normalize_account(account)

    if not project_id:
        project_id = get_project_id(access_token)

    quota_raw = get_quota(access_token, project_id)
    quota_formatted = format_quota(quota_raw, show_relative=True)
    filtered = filter_models(quota_formatted, ["gemini-3-flash"])
    return {"quota": filtered}


@app.get("/quota/claude-4-5")
async def get_claude_4_5():
    """Get Claude 4.5 models."""
    account = load_account()
    access_token = ensure_fresh_token(account)
    _, _, _, project_id = normalize_account(account)

    if not project_id:
        project_id = get_project_id(access_token)

    quota_raw = get_quota(access_token, project_id)
    quota_formatted = format_quota(quota_raw, show_relative=True)
    filtered = filter_models(
        quota_formatted, ["claude-opus-4-5-thinking", "claude-sonnet-4-5", "claude-sonnet-4-5-thinking"]
    )
    return {"quota": filtered}

