package main

import (
	"os"
	"path/filepath"
	"strconv"
)

const (
	// Token refresh buffer (5 minutes before expiry)
	TokenRefreshBufferSeconds = 300

	// Time conversion
	SecondsPerMinute = 60

	// Quota percentage thresholds for color coding
	QuotaFull     = 100
	QuotaGood     = 50
	QuotaWarning  = 20
	QuotaCritical = 1
)

// Config holds all configuration values
type Config struct {
	// Google Cloud Code API URLs
	APIURL        string
	ProjectAPIURL string
	TokenURL      string

	// User agent
	UserAgent string

	// Google OAuth credentials
	ClientID     string
	ClientSecret string

	// Account file path
	AccountFile string

	// Server port
	Port int

	// Query debounce time in minutes
	QueryDebounce int
}

// LoadConfig loads configuration from environment variables
func LoadConfig() *Config {
	config := &Config{
		APIURL:        "https://cloudcode-pa.googleapis.com/v1internal:fetchAvailableModels",
		ProjectAPIURL: "https://cloudcode-pa.googleapis.com/v1internal:loadCodeAssist",
		TokenURL:      "https://oauth2.googleapis.com/token",
		UserAgent:     getEnvOrDefault("USER_AGENT", "antigravity/1.13.3 Darwin/arm64"),
		ClientID:      os.Getenv("CLIENT_ID"),
		ClientSecret:  os.Getenv("CLIENT_SECRET"),
		AccountFile:   resolveAccountFile(getEnvOrDefault("ACCOUNT_FILE", "antigravity.json")),
		Port:          getEnvAsInt("PORT", 8000),
		QueryDebounce: getEnvAsInt("QUERY_DEBOUNCE", 1),
	}

	return config
}

func getEnvOrDefault(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvAsInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intValue, err := strconv.Atoi(value); err == nil {
			return intValue
		}
	}
	return defaultValue
}

func resolveAccountFile(accountFile string) string {
	// Remove quotes if present
	accountFile = trimQuotes(accountFile)
	
	// If absolute path, return as is
	if filepath.IsAbs(accountFile) {
		return accountFile
	}
	
	// Resolve relative to parent directory (project root)
	return filepath.Join("..", accountFile)
}

func trimQuotes(s string) string {
	if len(s) >= 2 {
		if (s[0] == '"' && s[len(s)-1] == '"') || (s[0] == '\'' && s[len(s)-1] == '\'') {
			return s[1 : len(s)-1]
		}
	}
	return s
}
