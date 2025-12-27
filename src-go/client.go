package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"sync"
	"time"
)

// Account represents the account structure
type Account struct {
	Token        *TokenData `json:"token,omitempty"`
	AccessToken  string     `json:"access_token,omitempty"`
	RefreshToken string     `json:"refresh_token,omitempty"`
	ProjectID    string     `json:"project_id,omitempty"`
	Timestamp    *int64     `json:"timestamp,omitempty"`
	ExpiresIn    int        `json:"expires_in,omitempty"`
	Type         string     `json:"type,omitempty"`
	Expired      string     `json:"expired,omitempty"`
}

// TokenData represents nested token structure
type TokenData struct {
	AccessToken     string `json:"access_token"`
	RefreshToken    string `json:"refresh_token"`
	ExpiryTimestamp *int64 `json:"expiry_timestamp,omitempty"`
	ProjectID       string `json:"project_id,omitempty"`
	ExpiresIn       int    `json:"expires_in,omitempty"`
	TokenType       string `json:"token_type,omitempty"`
}

// TokenResponse represents OAuth token response
type TokenResponse struct {
	AccessToken string `json:"access_token"`
	ExpiresIn   int    `json:"expires_in"`
	TokenType   string `json:"token_type"`
}

// QuotaResponse represents the API response structure
type QuotaResponse struct {
	Models map[string]ModelInfo `json:"models"`
}

// ModelInfo represents model information
type ModelInfo struct {
	QuotaInfo QuotaInfo `json:"quotaInfo"`
}

// QuotaInfo represents quota information
type QuotaInfo struct {
	RemainingFraction float64 `json:"remainingFraction"`
	ResetTime         string  `json:"resetTime"`
}

// FormattedModel represents formatted model data
type FormattedModel struct {
	Name                string `json:"name"`
	Percentage          int    `json:"percentage"`
	ResetTime           string `json:"reset_time"`
	ResetTimeRelative   string `json:"reset_time_relative,omitempty"`
}

// FormattedQuota represents formatted quota response
type FormattedQuota struct {
	Models      []FormattedModel `json:"models"`
	LastUpdated int64            `json:"last_updated"`
	IsForbidden bool             `json:"is_forbidden"`
}

// ProjectResponse represents project API response
type ProjectResponse struct {
	CloudAICompanionProject string `json:"cloudaicompanionproject"`
}

// CloudCodeClient handles API interactions
type CloudCodeClient struct {
	config     *Config
	httpClient *http.Client
	cache      map[string]interface{}
	cacheMutex sync.RWMutex
	cacheTime  time.Time
}

// NewCloudCodeClient creates a new client
func NewCloudCodeClient(config *Config) *CloudCodeClient {
	return &CloudCodeClient{
		config:     config,
		httpClient: &http.Client{Timeout: 30 * time.Second},
		cache:      make(map[string]interface{}),
	}
}

// LoadAccount loads account from file
func (c *CloudCodeClient) LoadAccount() (*Account, error) {
	data, err := os.ReadFile(c.config.AccountFile)
	if err != nil {
		return nil, fmt.Errorf("account file not found: %s", c.config.AccountFile)
	}

	var account Account
	if err := json.Unmarshal(data, &account); err != nil {
		return nil, fmt.Errorf("failed to parse account file: %v", err)
	}

	return &account, nil
}

// NormalizeAccount extracts token info from different account formats
func (c *CloudCodeClient) NormalizeAccount(account *Account) (string, string, *int64, string) {
	if account.Token != nil {
		return account.Token.AccessToken, account.Token.RefreshToken, account.Token.ExpiryTimestamp, account.Token.ProjectID
	}

	var expiryTimestamp *int64
	if account.Timestamp != nil && account.ExpiresIn > 0 {
		expiry := (*account.Timestamp / 1000) + int64(account.ExpiresIn)
		expiryTimestamp = &expiry
	}

	return account.AccessToken, account.RefreshToken, expiryTimestamp, account.ProjectID
}

// RefreshAccessToken refreshes the access token
func (c *CloudCodeClient) RefreshAccessToken(refreshToken string) (*TokenResponse, error) {
	data := map[string]string{
		"client_id":     c.config.ClientID,
		"client_secret": c.config.ClientSecret,
		"refresh_token": refreshToken,
		"grant_type":    "refresh_token",
	}

	jsonData, _ := json.Marshal(data)
	resp, err := c.httpClient.Post(c.config.TokenURL, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("token refresh failed: %d", resp.StatusCode)
	}

	var tokenResp TokenResponse
	if err := json.NewDecoder(resp.Body).Decode(&tokenResp); err != nil {
		return nil, err
	}

	return &tokenResp, nil
}

// EnsureFreshToken checks token expiry and refreshes if needed
func (c *CloudCodeClient) EnsureFreshToken(account *Account) (string, error) {
	accessToken, refreshToken, expiryTimestamp, _ := c.NormalizeAccount(account)

	if accessToken == "" || refreshToken == "" {
		return "", fmt.Errorf("missing access_token or refresh_token")
	}

	now := time.Now().Unix()
	if expiryTimestamp != nil && *expiryTimestamp > now+TokenRefreshBufferSeconds {
		log.Println("Token is fresh, no need to refresh")
		return accessToken, nil
	}

	// Token needs refresh
	log.Println("Token needs refresh")
	newToken, err := c.RefreshAccessToken(refreshToken)
	if err != nil {
		return "", err
	}

	newExpiry := now + int64(newToken.ExpiresIn)

	// Update account
	if account.Token != nil {
		account.Token.AccessToken = newToken.AccessToken
		account.Token.ExpiresIn = newToken.ExpiresIn
		account.Token.ExpiryTimestamp = &newExpiry
		account.Token.TokenType = newToken.TokenType
	} else {
		account.AccessToken = newToken.AccessToken
		account.ExpiresIn = newToken.ExpiresIn
		timestamp := now * 1000
		account.Timestamp = &timestamp
		account.Type = "antigravity"
	}

	// Update top-level fields
	expiryTime := time.Unix(newExpiry, 0)
	account.AccessToken = newToken.AccessToken
	account.Expired = expiryTime.Format(time.RFC3339)

	// Save updated account
	if err := c.saveAccount(account); err != nil {
		log.Printf("Failed to save refreshed token: %v", err)
	} else {
		log.Printf("Access token refreshed, expires at %s", expiryTime.Format(time.RFC3339))
	}

	return newToken.AccessToken, nil
}

// saveAccount saves account to file
func (c *CloudCodeClient) saveAccount(account *Account) error {
	data, err := json.MarshalIndent(account, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(c.config.AccountFile, data, 0600)
}

// GetProjectID fetches project ID from API
func (c *CloudCodeClient) GetProjectID(accessToken string) (string, error) {
	payload := map[string]interface{}{
		"metadata": map[string]string{
			"ideType": "ANTIGRAVITY",
		},
	}

	jsonData, _ := json.Marshal(payload)
	req, err := http.NewRequest("POST", c.config.ProjectAPIURL, bytes.NewBuffer(jsonData))
	if err != nil {
		return "", err
	}

	req.Header.Set("Authorization", "Bearer "+accessToken)
	req.Header.Set("User-Agent", c.config.UserAgent)
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("failed to get project ID: %d", resp.StatusCode)
	}

	var projectResp ProjectResponse
	if err := json.NewDecoder(resp.Body).Decode(&projectResp); err != nil {
		return "", err
	}

	return projectResp.CloudAICompanionProject, nil
}

// GetQuota fetches quota information with caching
func (c *CloudCodeClient) GetQuota(accessToken, projectID string) (*QuotaResponse, error) {
	cacheKey := "quota"

	// Check cache
	c.cacheMutex.RLock()
	if cached, exists := c.cache[cacheKey]; exists {
		if time.Since(c.cacheTime) < time.Duration(c.config.QueryDebounce)*time.Minute {
			c.cacheMutex.RUnlock()
			log.Println("Returning cached quota data")
			return cached.(*QuotaResponse), nil
		}
	}
	c.cacheMutex.RUnlock()

	// Fetch fresh data
	log.Println("Fetching fresh quota data from googleapis.com")
	payload := make(map[string]interface{})
	if projectID != "" {
		payload["project"] = projectID
	}

	jsonData, _ := json.Marshal(payload)
	req, err := http.NewRequest("POST", c.config.APIURL, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, err
	}

	req.Header.Set("Authorization", "Bearer "+accessToken)
	req.Header.Set("User-Agent", c.config.UserAgent)
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("API request failed: %d - %s", resp.StatusCode, string(body))
	}

	var quotaResp QuotaResponse
	if err := json.NewDecoder(resp.Body).Decode(&quotaResp); err != nil {
		return nil, err
	}

	// Update cache
	c.cacheMutex.Lock()
	c.cache[cacheKey] = &quotaResp
	c.cacheTime = time.Now()
	c.cacheMutex.Unlock()

	log.Printf("Cached quota data for %d minute(s)", c.config.QueryDebounce)
	return &quotaResp, nil
}
