"""FastAPI server for Antigravity quota queries.

Endpoints:
- GET /quota/overview - Quick summary ("Pro 95% | Flash 90% | Claude 80%")
- GET /quota/all - All models with relative reset time
- GET /quota/pro - Gemini 3 Pro models (high, image, low)
- GET /quota/flash - Gemini 3 Flash model
- GET /quota/claude - Claude 4.5 models
"""

import time
import tomllib
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException

from .cloudcode_client import (
    ensure_fresh_token,
    get_project_id,
    get_quota,
    load_account,
    normalize_account,
)


def _get_version() -> str:
    """Read version from pyproject.toml."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


app = FastAPI(
    title="Antigravity Quota API",
    version=_get_version(),
)


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
    except Exception:
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


def _get_quota_data():
    """Helper to load account and fetch quota."""
    try:
        account = load_account()
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        access_token = ensure_fresh_token(account)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    _, _, _, project_id = normalize_account(account)

    if not project_id:
        project_id = get_project_id(access_token)

    return get_quota(access_token, project_id)


@app.get("/quota")
async def get_quota_endpoints():
    """Return available quota API endpoints."""
    return {
        "message": "Welcome to the Antigravity Quota API",
        "endpoints": {
            "/quota": "This endpoint - lists all available endpoints",
            "/quota/overview": "Quick summary (e.g., 'Pro 95% | Flash 90% | Claude 80%')",
            "/quota/all": "All models with percentage and relative reset time",
            "/quota/pro": "Gemini 3 Pro models (high, image, low)",
            "/quota/flash": "Gemini 3 Flash model",
            "/quota/claude": "Claude 4.5 models (opus, sonnet, thinking)",
        },
    }


@app.get("/quota/usage")
async def get_quota_usage():
    """Return available quota API endpoints (alias for /quota)."""
    return await get_quota_endpoints()


@app.get("/quota/overview")
async def get_quota_overview():
    """Get quick quota summary as string (e.g., 'Pro 95% | Flash 90% | Claude 80%')."""
    quota_raw = _get_quota_data()
    quota_formatted = format_quota(quota_raw, show_relative=False)

    # Get Pro average (gemini-3-pro-high)
    pro_models = [m for m in quota_formatted["models"] if "gemini-3-pro-high" in m["name"].lower()]
    pro_pct = pro_models[0]["percentage"] if pro_models else 0

    # Get Flash (gemini-3-flash)
    flash_models = [m for m in quota_formatted["models"] if "gemini-3-flash" in m["name"].lower()]
    flash_pct = flash_models[0]["percentage"] if flash_models else 0

    # Get Claude average (claude-sonnet-4-5, non-thinking)
    claude_models = [m for m in quota_formatted["models"] if m["name"].lower() == "claude-sonnet-4-5"]
    claude_pct = claude_models[0]["percentage"] if claude_models else 0

    return {"overview": f"Pro {pro_pct}% | Flash {flash_pct}% | Claude {claude_pct}%"}


@app.get("/quota/all")
async def get_all_quota():
    """Get all models with relative reset time."""
    quota_raw = _get_quota_data()
    return {"quota": format_quota(quota_raw, show_relative=True)}


@app.get("/quota/pro")
async def get_gemini_3_pro():
    """Get Gemini 3 Pro models (high, image, low)."""
    quota_raw = _get_quota_data()
    quota_formatted = format_quota(quota_raw, show_relative=True)
    filtered = filter_models(quota_formatted, ["gemini-3-pro-high", "gemini-3-pro-image", "gemini-3-pro-low"])
    return {"quota": filtered}


@app.get("/quota/flash")
async def get_gemini_3_flash():
    """Get Gemini 3 Flash model."""
    quota_raw = _get_quota_data()
    quota_formatted = format_quota(quota_raw, show_relative=True)
    filtered = filter_models(quota_formatted, ["gemini-3-flash"])
    return {"quota": filtered}


@app.get("/quota/claude")
async def get_claude_4_5():
    """Get Claude 4.5 models."""
    quota_raw = _get_quota_data()
    quota_formatted = format_quota(quota_raw, show_relative=True)
    filtered = filter_models(
        quota_formatted, ["claude-opus-4-5-thinking", "claude-sonnet-4-5", "claude-sonnet-4-5-thinking"]
    )
    return {"quota": filtered}
