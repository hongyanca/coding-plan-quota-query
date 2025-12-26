"""Tests for src.api module."""

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api import (
    app,
    filter_models,
    format_percentage_with_color,
    format_quota,
    format_time_compact,
    format_time_remaining,
)


class TestFormatTimeRemaining:
    """Tests for format_time_remaining function."""

    def test_future_time(self):
        """Test formatting a future reset time."""
        future = datetime.now(timezone.utc) + timedelta(hours=4, minutes=30)
        result = format_time_remaining(future.isoformat())
        # Allow for test execution time (could be 4h 29m or 4h 30m)
        assert result in ("4h 29m", "4h 30m")

    def test_past_time_returns_reset_due(self):
        """Test that past time returns 'Reset due'."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        result = format_time_remaining(past.isoformat())
        assert result == "Reset due"

    def test_z_suffix_timezone(self):
        """Test parsing time with Z suffix."""
        future = datetime.now(timezone.utc) + timedelta(hours=2, minutes=15)
        time_str = future.strftime("%Y-%m-%dT%H:%M:%SZ")
        result = format_time_remaining(time_str)
        # Allow for test execution time (could be 2h 14m or 2h 15m)
        assert result in ("2h 14m", "2h 15m")

    def test_invalid_time_returns_empty(self):
        """Test that invalid time string returns empty string."""
        result = format_time_remaining("invalid-time")
        assert result == ""


class TestFormatTimeCompact:
    """Tests for format_time_compact function."""

    def test_hours_and_minutes(self):
        """Test compact format with hours and minutes."""
        future = datetime.now(timezone.utc) + timedelta(hours=2, minutes=18)
        result = format_time_compact(future.isoformat())
        assert result in ("2h17m", "2h18m")

    def test_only_hours(self):
        """Test compact format with only hours (0 minutes)."""
        future = datetime.now(timezone.utc) + timedelta(hours=3, seconds=30)
        result = format_time_compact(future.isoformat())
        assert result == "3h"

    def test_only_minutes(self):
        """Test compact format with only minutes (0 hours)."""
        future = datetime.now(timezone.utc) + timedelta(minutes=45, seconds=30)
        result = format_time_compact(future.isoformat())
        assert result in ("45m", "44m")

    def test_past_time_returns_empty(self):
        """Test that past time returns empty string."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        result = format_time_compact(past.isoformat())
        assert result == ""

    def test_invalid_time_returns_empty(self):
        """Test that invalid time string returns empty string."""
        result = format_time_compact("invalid-time")
        assert result == ""


class TestFormatPercentageWithColor:
    """Tests for format_percentage_with_color function."""

    # ANSI codes for verification
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    RESET = "\033[0m"

    def test_100_percent_green_dot(self):
        """Test 100% returns green dot symbol."""
        result = format_percentage_with_color(100)
        assert result == f"{self.GREEN}●{self.RESET}"
        assert "100%" not in result

    def test_0_percent_red_dot(self):
        """Test 0% returns red dot symbol."""
        result = format_percentage_with_color(0)
        assert result == f"{self.RED}●{self.RESET}"
        assert "0%" not in result

    def test_50_to_99_green_percentage(self):
        """Test 50-99% returns green colored percentage."""
        for pct in [50, 75, 99]:
            result = format_percentage_with_color(pct)
            assert result == f"{self.GREEN}{pct}%{self.RESET}"

    def test_20_to_49_yellow_percentage(self):
        """Test 20-49% returns yellow colored percentage."""
        for pct in [20, 35, 49]:
            result = format_percentage_with_color(pct)
            assert result == f"{self.YELLOW}{pct}%{self.RESET}"

    def test_1_to_19_red_percentage(self):
        """Test 1-19% returns red colored percentage."""
        for pct in [1, 10, 19]:
            result = format_percentage_with_color(pct)
            assert result == f"{self.RED}{pct}%{self.RESET}"


class TestFormatQuota:
    """Tests for format_quota function."""

    def test_format_gemini_models(self):
        """Test formatting Gemini models."""
        quota_data = {
            "models": {
                "gemini-3-pro-high": {
                    "quotaInfo": {
                        "remainingFraction": 0.85,
                        "resetTime": "2025-12-26T00:00:00Z",
                    }
                },
                "gemini-3-flash": {
                    "quotaInfo": {
                        "remainingFraction": 1.0,
                        "resetTime": "2025-12-26T00:00:00Z",
                    }
                },
            }
        }
        result = format_quota(quota_data, show_relative=False)

        assert len(result["models"]) == 2
        assert result["models"][0]["name"] == "gemini-3-flash"
        assert result["models"][0]["percentage"] == 100
        assert result["models"][1]["name"] == "gemini-3-pro-high"
        assert result["models"][1]["percentage"] == 85
        assert result["is_forbidden"] is False

    def test_format_claude_models(self):
        """Test formatting Claude models."""
        quota_data = {
            "models": {
                "claude-sonnet-4-5": {
                    "quotaInfo": {
                        "remainingFraction": 0.50,
                        "resetTime": "2025-12-26T00:00:00Z",
                    }
                },
            }
        }
        result = format_quota(quota_data, show_relative=False)

        assert len(result["models"]) == 1
        assert result["models"][0]["name"] == "claude-sonnet-4-5"
        assert result["models"][0]["percentage"] == 50

    def test_filters_non_gemini_claude_models(self):
        """Test that non-Gemini/Claude models are filtered out."""
        quota_data = {
            "models": {
                "some-other-model": {
                    "quotaInfo": {
                        "remainingFraction": 0.75,
                        "resetTime": "2025-12-26T00:00:00Z",
                    }
                },
            }
        }
        result = format_quota(quota_data, show_relative=False)
        assert len(result["models"]) == 0

    def test_empty_models(self):
        """Test handling empty models dict."""
        quota_data = {"models": {}}
        result = format_quota(quota_data)
        assert result["models"] == []
        assert "last_updated" in result


class TestFilterModels:
    """Tests for filter_models function."""

    def test_filter_by_pattern(self):
        """Test filtering models by pattern."""
        quota = {
            "models": [
                {"name": "gemini-3-pro-high", "percentage": 100},
                {"name": "gemini-3-pro-low", "percentage": 90},
                {"name": "gemini-3-flash", "percentage": 80},
                {"name": "claude-sonnet-4-5", "percentage": 70},
            ],
            "last_updated": 123456,
            "is_forbidden": False,
        }
        result = filter_models(quota, ["gemini-3-pro"])
        assert len(result["models"]) == 2
        assert all("gemini-3-pro" in m["name"] for m in result["models"])
        assert result["last_updated"] == 123456

    def test_filter_multiple_patterns(self):
        """Test filtering with multiple patterns."""
        quota = {
            "models": [
                {"name": "gemini-3-pro-high", "percentage": 100},
                {"name": "claude-sonnet-4-5", "percentage": 70},
            ],
            "last_updated": 123456,
            "is_forbidden": False,
        }
        result = filter_models(quota, ["gemini", "claude"])
        assert len(result["models"]) == 2

    def test_filter_no_matches(self):
        """Test filtering with no matches."""
        quota = {
            "models": [{"name": "gemini-3-pro-high", "percentage": 100}],
            "last_updated": 123456,
            "is_forbidden": False,
        }
        result = filter_models(quota, ["nonexistent"])
        assert len(result["models"]) == 0


class TestAPIEndpoints:
    """Integration tests for API endpoints using mocked data."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_quota_data(self):
        """Sample quota data for mocking."""
        return {
            "models": {
                "gemini-3-pro-high": {
                    "quotaInfo": {
                        "remainingFraction": 1.0,
                        "resetTime": "2025-12-26T00:00:00Z",
                    }
                },
                "gemini-3-flash": {
                    "quotaInfo": {
                        "remainingFraction": 0.9,
                        "resetTime": "2025-12-26T00:00:00Z",
                    }
                },
                "claude-sonnet-4-5": {
                    "quotaInfo": {
                        "remainingFraction": 0.8,
                        "resetTime": "2025-12-26T00:00:00Z",
                    }
                },
            }
        }

    @patch("src.api._get_quota_data")
    def test_get_all_quota(self, mock_get_quota, client, mock_quota_data):
        """Test /quota/all endpoint returns all models."""
        mock_get_quota.return_value = mock_quota_data

        response = client.get("/quota/all")

        assert response.status_code == 200
        data = response.json()
        assert "quota" in data
        assert len(data["quota"]["models"]) == 3

    @patch("src.api._get_quota_data")
    def test_get_gemini_3_pro(self, mock_get_quota, client, mock_quota_data):
        """Test /quota/pro endpoint."""
        mock_get_quota.return_value = mock_quota_data

        response = client.get("/quota/pro")

        assert response.status_code == 200
        data = response.json()
        assert len(data["quota"]["models"]) == 1
        assert "gemini-3-pro" in data["quota"]["models"][0]["name"]

    @patch("src.api._get_quota_data")
    def test_get_gemini_3_flash(self, mock_get_quota, client, mock_quota_data):
        """Test /quota/flash endpoint."""
        mock_get_quota.return_value = mock_quota_data

        response = client.get("/quota/flash")

        assert response.status_code == 200
        data = response.json()
        assert len(data["quota"]["models"]) == 1
        assert data["quota"]["models"][0]["name"] == "gemini-3-flash"

    @patch("src.api._get_quota_data")
    def test_get_claude_4_5(self, mock_get_quota, client, mock_quota_data):
        """Test /quota/claude endpoint."""
        mock_get_quota.return_value = mock_quota_data

        response = client.get("/quota/claude")

        assert response.status_code == 200
        data = response.json()
        assert len(data["quota"]["models"]) == 1
        assert "claude" in data["quota"]["models"][0]["name"]


class TestQuotaStatusEndpoint:
    """Tests for /quota/status endpoint with various quota scenarios."""

    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    RESET = "\033[0m"

    # Nerdfont icons
    GEMINI_ICON = "󰊭"
    FLASH_ICON = ""
    CLAUDE_ICON = "󰛄"

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def _make_quota_data(self, pro_pct, flash_pct, claude_pct):
        """Helper to create mock quota data with specific percentages."""
        future = datetime.now(timezone.utc) + timedelta(hours=2, minutes=18)
        reset_time = future.isoformat()
        return {
            "models": {
                "gemini-3-pro-high": {
                    "quotaInfo": {
                        "remainingFraction": pro_pct / 100,
                        "resetTime": reset_time,
                    }
                },
                "gemini-3-flash": {
                    "quotaInfo": {
                        "remainingFraction": flash_pct / 100,
                        "resetTime": reset_time,
                    }
                },
                "claude-sonnet-4-5": {
                    "quotaInfo": {
                        "remainingFraction": claude_pct / 100,
                        "resetTime": reset_time,
                    }
                },
            }
        }

    @patch("src.api._get_quota_data")
    def test_all_100_percent(self, mock_get_quota, client):
        """Test all models at 100% - green icons, no time."""
        mock_get_quota.return_value = self._make_quota_data(100, 100, 100)

        response = client.get("/quota/status")

        assert response.status_code == 200
        overview = response.json()["overview"]
        # Should have green colored icons for all
        assert f"{self.GREEN}{self.GEMINI_ICON}{self.RESET}" in overview
        assert f"{self.GREEN}{self.FLASH_ICON}{self.RESET}" in overview
        assert f"{self.GREEN}{self.CLAUDE_ICON}{self.RESET}" in overview
        # Should not have percentage text
        assert "100%" not in overview
        # Check no time format present - strip ANSI codes first
        import re
        clean_overview = re.sub(r"\x1b\[[0-9;]*m", "", overview)
        assert not re.search(r"\d+h", clean_overview)
        assert not re.search(r"\d+m", clean_overview)

    @patch("src.api._get_quota_data")
    def test_all_0_percent(self, mock_get_quota, client):
        """Test all models at 0% - red icons."""
        mock_get_quota.return_value = self._make_quota_data(0, 0, 0)

        response = client.get("/quota/status")

        assert response.status_code == 200
        overview = response.json()["overview"]
        # Should have red colored icons for all
        assert f"{self.RED}{self.GEMINI_ICON}{self.RESET}" in overview
        assert f"{self.RED}{self.FLASH_ICON}{self.RESET}" in overview
        assert f"{self.RED}{self.CLAUDE_ICON}{self.RESET}" in overview
        # Should not have "0%" text
        assert "0%" not in overview

    @patch("src.api._get_quota_data")
    def test_mixed_quotas_green_range(self, mock_get_quota, client):
        """Test models in 50-99% range - green percentages with time."""
        mock_get_quota.return_value = self._make_quota_data(75, 90, 55)

        response = client.get("/quota/status")

        assert response.status_code == 200
        overview = response.json()["overview"]
        # Should have green percentages
        assert f"{self.GREEN}75%{self.RESET}" in overview
        assert f"{self.GREEN}90%{self.RESET}" in overview
        assert f"{self.GREEN}55%{self.RESET}" in overview
        # Should have time (2h18m or 2h17m)
        assert "2h" in overview

    @patch("src.api._get_quota_data")
    def test_yellow_range(self, mock_get_quota, client):
        """Test models in 20-49% range - yellow percentages."""
        mock_get_quota.return_value = self._make_quota_data(35, 45, 25)

        response = client.get("/quota/status")

        assert response.status_code == 200
        overview = response.json()["overview"]
        # Should have yellow percentages
        assert f"{self.YELLOW}35%{self.RESET}" in overview
        assert f"{self.YELLOW}45%{self.RESET}" in overview
        assert f"{self.YELLOW}25%{self.RESET}" in overview

    @patch("src.api._get_quota_data")
    def test_red_range(self, mock_get_quota, client):
        """Test models in 1-19% range - red percentages."""
        mock_get_quota.return_value = self._make_quota_data(5, 15, 1)

        response = client.get("/quota/status")

        assert response.status_code == 200
        overview = response.json()["overview"]
        # Should have red percentages
        assert f"{self.RED}5%{self.RESET}" in overview
        assert f"{self.RED}15%{self.RESET}" in overview
        assert f"{self.RED}1%{self.RESET}" in overview

    @patch("src.api._get_quota_data")
    def test_mixed_all_ranges(self, mock_get_quota, client):
        """Test mixed quotas across all color ranges."""
        mock_get_quota.return_value = self._make_quota_data(100, 45, 5)

        response = client.get("/quota/status")

        assert response.status_code == 200
        overview = response.json()["overview"]
        # Pro at 100% - green icon, no time
        assert f"{self.GREEN}{self.GEMINI_ICON}{self.RESET}" in overview
        # Flash at 45% - icon + yellow percentage with time
        assert f"{self.YELLOW}45%{self.RESET}" in overview
        assert self.FLASH_ICON in overview
        # Claude at 5% - icon + red percentage with time
        assert f"{self.RED}5%{self.RESET}" in overview
        assert self.CLAUDE_ICON in overview

