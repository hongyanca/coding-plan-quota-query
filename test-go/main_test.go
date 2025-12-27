package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
	"time"
)

// Import the main package types and functions
// Since we're testing in the same package, we can access unexported functions

func TestLoadConfig(t *testing.T) {
	// Test default values
	config := LoadConfig()
	
	if config.APIURL != "https://cloudcode-pa.googleapis.com/v1internal:fetchAvailableModels" {
		t.Errorf("Expected default API URL, got %s", config.APIURL)
	}
	
	if config.Port != 8000 {
		t.Errorf("Expected default port 8000, got %d", config.Port)
	}
	
	if config.QueryDebounce != 1 {
		t.Errorf("Expected default query debounce 1, got %d", config.QueryDebounce)
	}
}

func TestNormalizeAccount(t *testing.T) {
	client := NewCloudCodeClient(LoadConfig())
	
	// Test nested token structure
	account := &Account{
		Token: &TokenData{
			AccessToken:     "test-access",
			RefreshToken:    "test-refresh",
			ExpiryTimestamp: func() *int64 { t := int64(1234567890); return &t }(),
			ProjectID:       "test-project",
		},
	}
	
	accessToken, refreshToken, expiryTimestamp, projectID := client.NormalizeAccount(account)
	
	if accessToken != "test-access" {
		t.Errorf("Expected access token 'test-access', got %s", accessToken)
	}
	
	if refreshToken != "test-refresh" {
		t.Errorf("Expected refresh token 'test-refresh', got %s", refreshToken)
	}
	
	if expiryTimestamp == nil || *expiryTimestamp != 1234567890 {
		t.Errorf("Expected expiry timestamp 1234567890, got %v", expiryTimestamp)
	}
	
	if projectID != "test-project" {
		t.Errorf("Expected project ID 'test-project', got %s", projectID)
	}
}

func TestFormatTimeRemaining(t *testing.T) {
	// Test with future time
	future := time.Now().UTC().Add(2*time.Hour + 30*time.Minute)
	resetTime := future.Format(time.RFC3339)
	
	result := formatTimeRemaining(resetTime)
	// Allow for small timing differences (2h 29m or 2h 30m)
	if result != "2h 30m" && result != "2h 29m" {
		t.Errorf("Expected '2h 30m' or '2h 29m', got %s", result)
	}
	
	// Test with past time
	past := time.Now().UTC().Add(-1 * time.Hour)
	resetTime = past.Format(time.RFC3339)
	
	result = formatTimeRemaining(resetTime)
	if result != "Reset due" {
		t.Errorf("Expected 'Reset due', got %s", result)
	}
	
	// Test with empty string
	result = formatTimeRemaining("")
	if result != "" {
		t.Errorf("Expected empty string, got %s", result)
	}
}

func TestFormatQuota(t *testing.T) {
	quotaData := &QuotaResponse{
		Models: map[string]ModelInfo{
			"gemini-3-pro-high": {
				QuotaInfo: QuotaInfo{
					RemainingFraction: 0.95,
					ResetTime:         "2025-12-26T10:00:00Z",
				},
			},
			"claude-sonnet-4-5": {
				QuotaInfo: QuotaInfo{
					RemainingFraction: 0.80,
					ResetTime:         "2025-12-26T12:00:00Z",
				},
			},
			"some-other-model": {
				QuotaInfo: QuotaInfo{
					RemainingFraction: 0.50,
					ResetTime:         "2025-12-26T14:00:00Z",
				},
			},
		},
	}
	
	formatted := formatQuota(quotaData, true)
	
	// Should only include gemini and claude models
	if len(formatted.Models) != 2 {
		t.Errorf("Expected 2 models, got %d", len(formatted.Models))
	}
	
	// Check percentages
	for _, model := range formatted.Models {
		if model.Name == "gemini-3-pro-high" && model.Percentage != 95 {
			t.Errorf("Expected 95%% for gemini-3-pro-high, got %d%%", model.Percentage)
		}
		if model.Name == "claude-sonnet-4-5" && model.Percentage != 80 {
			t.Errorf("Expected 80%% for claude-sonnet-4-5, got %d%%", model.Percentage)
		}
	}
}

func TestFilterModels(t *testing.T) {
	quota := &FormattedQuota{
		Models: []FormattedModel{
			{Name: "gemini-3-pro-high", Percentage: 95},
			{Name: "gemini-3-flash", Percentage: 90},
			{Name: "claude-sonnet-4-5", Percentage: 80},
		},
		LastUpdated: time.Now().Unix(),
		IsForbidden: false,
	}
	
	filtered := filterModels(quota, []string{"gemini-3-pro-high", "gemini-3-flash"})
	
	if len(filtered.Models) != 2 {
		t.Errorf("Expected 2 filtered models, got %d", len(filtered.Models))
	}
	
	// Check that only gemini models are included
	for _, model := range filtered.Models {
		if model.Name != "gemini-3-pro-high" && model.Name != "gemini-3-flash" {
			t.Errorf("Unexpected model in filtered results: %s", model.Name)
		}
	}
}

func TestLoadAccount(t *testing.T) {
	// Create temporary account file
	tmpDir := t.TempDir()
	accountFile := filepath.Join(tmpDir, "test-account.json")
	
	testAccount := Account{
		AccessToken:  "test-access",
		RefreshToken: "test-refresh",
		ProjectID:    "test-project",
	}
	
	data, _ := json.MarshalIndent(testAccount, "", "  ")
	err := os.WriteFile(accountFile, data, 0600)
	if err != nil {
		t.Fatalf("Failed to create test account file: %v", err)
	}
	
	// Test loading
	config := &Config{AccountFile: accountFile}
	client := NewCloudCodeClient(config)
	
	account, err := client.LoadAccount()
	if err != nil {
		t.Fatalf("Failed to load account: %v", err)
	}
	
	if account.AccessToken != "test-access" {
		t.Errorf("Expected access token 'test-access', got %s", account.AccessToken)
	}
	
	if account.RefreshToken != "test-refresh" {
		t.Errorf("Expected refresh token 'test-refresh', got %s", account.RefreshToken)
	}
	
	if account.ProjectID != "test-project" {
		t.Errorf("Expected project ID 'test-project', got %s", account.ProjectID)
	}
}
