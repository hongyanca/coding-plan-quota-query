package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"

	"github.com/gin-gonic/gin"
)

func TestMain(m *testing.M) {
	// Set Gin to test mode
	gin.SetMode(gin.TestMode)
	os.Exit(m.Run())
}

func setupTestRouter() *gin.Engine {
	r := gin.New()
	setupRoutes(r)
	return r
}

func createTestAccount(t *testing.T) string {
	tmpDir := t.TempDir()
	accountFile := filepath.Join(tmpDir, "test-account.json")
	
	testAccount := Account{
		AccessToken:  "test-access-token",
		RefreshToken: "test-refresh-token",
		ProjectID:    "test-project-id",
		ExpiresIn:    3600,
	}
	
	data, _ := json.MarshalIndent(testAccount, "", "  ")
	err := os.WriteFile(accountFile, data, 0600)
	if err != nil {
		t.Fatalf("Failed to create test account file: %v", err)
	}
	
	return accountFile
}

func TestGetQuotaEndpoints(t *testing.T) {
	router := setupTestRouter()
	
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/quota", nil)
	router.ServeHTTP(w, req)
	
	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}
	
	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to parse response: %v", err)
	}
	
	if response["message"] != "Welcome to the Antigravity Quota API" {
		t.Errorf("Unexpected message in response")
	}
	
	endpoints, ok := response["endpoints"].(map[string]interface{})
	if !ok {
		t.Errorf("Expected endpoints object in response")
	}
	
	if len(endpoints) == 0 {
		t.Errorf("Expected endpoints to be populated")
	}
}

func TestGetQuotaUsage(t *testing.T) {
	router := setupTestRouter()
	
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/quota/usage", nil)
	router.ServeHTTP(w, req)
	
	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}
	
	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to parse response: %v", err)
	}
	
	// Should be same as /quota endpoint
	if response["message"] != "Welcome to the Antigravity Quota API" {
		t.Errorf("Unexpected message in response")
	}
}

// Mock HTTP server for testing API calls
func createMockServer(t *testing.T) *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/v1internal:fetchAvailableModels":
			response := QuotaResponse{
				Models: map[string]ModelInfo{
					"gemini-3-pro-high": {
						QuotaInfo: QuotaInfo{
							RemainingFraction: 0.95,
							ResetTime:         "2025-12-26T10:00:00Z",
						},
					},
					"gemini-3-flash": {
						QuotaInfo: QuotaInfo{
							RemainingFraction: 0.90,
							ResetTime:         "2025-12-26T11:00:00Z",
						},
					},
					"claude-sonnet-4-5": {
						QuotaInfo: QuotaInfo{
							RemainingFraction: 0.80,
							ResetTime:         "2025-12-26T12:00:00Z",
						},
					},
				},
			}
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(response)
		case "/v1internal:loadCodeAssist":
			response := ProjectResponse{
				CloudAICompanionProject: "test-project-id",
			}
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(response)
		case "/token":
			response := TokenResponse{
				AccessToken: "new-access-token",
				ExpiresIn:   3600,
				TokenType:   "Bearer",
			}
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(response)
		default:
			w.WriteHeader(http.StatusNotFound)
		}
	}))
}

func TestQuotaServiceWithMockServer(t *testing.T) {
	// Create mock server
	mockServer := createMockServer(t)
	defer mockServer.Close()
	
	// Create test account
	accountFile := createTestAccount(t)
	
	// Create config with mock server URLs
	config := &Config{
		APIURL:        mockServer.URL + "/v1internal:fetchAvailableModels",
		ProjectAPIURL: mockServer.URL + "/v1internal:loadCodeAssist",
		TokenURL:      mockServer.URL + "/token",
		UserAgent:     "test-agent",
		ClientID:      "test-client-id",
		ClientSecret:  "test-client-secret",
		AccountFile:   accountFile,
		QueryDebounce: 1,
	}
	
	client := NewCloudCodeClient(config)
	
	// Test loading account
	_, err := client.LoadAccount()
	if err != nil {
		t.Fatalf("Failed to load account: %v", err)
	}
	
	// Test getting quota (this will use cached token since it's not expired)
	quotaResp, err := client.GetQuota("test-access-token", "test-project-id")
	if err != nil {
		t.Fatalf("Failed to get quota: %v", err)
	}
	
	if len(quotaResp.Models) != 3 {
		t.Errorf("Expected 3 models, got %d", len(quotaResp.Models))
	}
	
	// Test formatting
	formatted := formatQuota(quotaResp, true)
	if len(formatted.Models) != 3 {
		t.Errorf("Expected 3 formatted models, got %d", len(formatted.Models))
	}
	
	// Test filtering
	proModels := filterModels(formatted, []string{"gemini-3-pro-high"})
	if len(proModels.Models) != 1 {
		t.Errorf("Expected 1 pro model, got %d", len(proModels.Models))
	}
	
	if proModels.Models[0].Name != "gemini-3-pro-high" {
		t.Errorf("Expected gemini-3-pro-high, got %s", proModels.Models[0].Name)
	}
	
	if proModels.Models[0].Percentage != 95 {
		t.Errorf("Expected 95%%, got %d%%", proModels.Models[0].Percentage)
	}
}

func TestFormatTimeCompact(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{"empty", "", ""},
		{"2h30m", "2025-12-26T12:30:00Z", ""},  // This will vary based on current time
		{"invalid", "invalid-time", ""},
	}
	
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := formatTimeCompact(tt.input)
			if tt.name == "empty" || tt.name == "invalid" {
				if result != tt.expected {
					t.Errorf("Expected %s, got %s", tt.expected, result)
				}
			}
			// For time-based tests, we just check it doesn't panic
		})
	}
}

func TestFormatPercentageWithColor(t *testing.T) {
	tests := []struct {
		percentage int
		contains   string
	}{
		{100, "●"},
		{75, "75%"},
		{25, "25%"},
		{5, "5%"},
		{0, "●"},
	}
	
	for _, tt := range tests {
		t.Run("", func(t *testing.T) {
			result := formatPercentageWithColor(tt.percentage)
			if !bytes.Contains([]byte(result), []byte(tt.contains)) {
				t.Errorf("Expected result to contain %s, got %s", tt.contains, result)
			}
		})
	}
}
