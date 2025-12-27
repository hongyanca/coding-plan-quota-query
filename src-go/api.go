package main

import (
	"fmt"
	"net/http"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
)

// QuotaService handles quota-related operations
type QuotaService struct {
	client *CloudCodeClient
}

// NewQuotaService creates a new quota service
func NewQuotaService(client *CloudCodeClient) *QuotaService {
	return &QuotaService{client: client}
}

// setupRoutes configures all API routes
func setupRoutes(r *gin.Engine) {
	config := LoadConfig()
	client := NewCloudCodeClient(config)
	service := NewQuotaService(client)

	quota := r.Group("/quota")
	{
		quota.GET("", service.GetQuotaEndpoints)
		quota.GET("/usage", service.GetQuotaEndpoints)
		quota.GET("/overview", service.GetQuotaOverview)
		quota.GET("/status", service.GetQuotaStatus)
		quota.GET("/all", service.GetAllQuota)
		quota.GET("/pro", service.GetGemini3Pro)
		quota.GET("/flash", service.GetGemini3Flash)
		quota.GET("/claude", service.GetClaude45)
	}
}

// GetQuotaEndpoints returns available endpoints
func (s *QuotaService) GetQuotaEndpoints(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"message": "Welcome to the Antigravity Quota API",
		"endpoints": gin.H{
			"/quota":          "This endpoint - lists all available endpoints",
			"/quota/overview": "Quick summary (e.g., 'Pro 95% | Flash 90% | Claude 80%')",
			"/quota/status":   "Terminal status with nerdfont icons and colors",
			"/quota/all":      "All models with percentage and relative reset time",
			"/quota/pro":      "Gemini 3 Pro models (high, image, low)",
			"/quota/flash":    "Gemini 3 Flash model",
			"/quota/claude":   "Claude 4.5 models (opus, sonnet, thinking)",
		},
	})
}

// getQuotaData helper function to load account and fetch quota
func (s *QuotaService) getQuotaData() (*QuotaResponse, error) {
	account, err := s.client.LoadAccount()
	if err != nil {
		return nil, err
	}

	accessToken, err := s.client.EnsureFreshToken(account)
	if err != nil {
		return nil, err
	}

	_, _, _, projectID := s.client.NormalizeAccount(account)
	if projectID == "" {
		projectID, _ = s.client.GetProjectID(accessToken)
	}

	return s.client.GetQuota(accessToken, projectID)
}

// formatTimeRemaining calculates time remaining until reset
func formatTimeRemaining(resetTime string) string {
	if resetTime == "" {
		return ""
	}

	resetDt, err := time.Parse(time.RFC3339, resetTime)
	if err != nil {
		// Try parsing with Z suffix
		resetDt, err = time.Parse("2006-01-02T15:04:05Z", resetTime)
		if err != nil {
			return ""
		}
	}

	now := time.Now().UTC()
	delta := resetDt.Sub(now)

	if delta <= 0 {
		return "Reset due"
	}

	hours := int(delta.Hours())
	minutes := int(delta.Minutes()) % 60
	return fmt.Sprintf("%dh %dm", hours, minutes)
}

// formatQuota formats quota data to match Python implementation
func formatQuota(quotaData *QuotaResponse, showRelative bool) *FormattedQuota {
	var models []FormattedModel

	for name, info := range quotaData.Models {
		remainingFraction := info.QuotaInfo.RemainingFraction
		resetTime := info.QuotaInfo.ResetTime

		nameLower := strings.ToLower(name)
		if strings.Contains(nameLower, "gemini") || strings.Contains(nameLower, "claude") {
			model := FormattedModel{
				Name:       name,
				Percentage: int(remainingFraction * 100),
				ResetTime:  resetTime,
			}
			if showRelative && resetTime != "" {
				model.ResetTimeRelative = formatTimeRemaining(resetTime)
			}
			models = append(models, model)
		}
	}

	// Sort models by name
	sort.Slice(models, func(i, j int) bool {
		return models[i].Name < models[j].Name
	})

	return &FormattedQuota{
		Models:      models,
		LastUpdated: time.Now().Unix(),
		IsForbidden: false,
	}
}

// filterModels filters models by name patterns
func filterModels(quota *FormattedQuota, patterns []string) *FormattedQuota {
	var filtered []FormattedModel

	for _, model := range quota.Models {
		nameLower := strings.ToLower(model.Name)
		for _, pattern := range patterns {
			if strings.Contains(nameLower, strings.ToLower(pattern)) {
				filtered = append(filtered, model)
				break
			}
		}
	}

	return &FormattedQuota{
		Models:      filtered,
		LastUpdated: quota.LastUpdated,
		IsForbidden: quota.IsForbidden,
	}
}

// GetQuotaOverview returns quick quota summary
func (s *QuotaService) GetQuotaOverview(c *gin.Context) {
	quotaRaw, err := s.getQuotaData()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	quotaFormatted := formatQuota(quotaRaw, false)

	// Get Pro average (gemini-3-pro-high)
	proPct := 0
	for _, model := range quotaFormatted.Models {
		if strings.Contains(strings.ToLower(model.Name), "gemini-3-pro-high") {
			proPct = model.Percentage
			break
		}
	}

	// Get Flash (gemini-3-flash)
	flashPct := 0
	for _, model := range quotaFormatted.Models {
		if strings.Contains(strings.ToLower(model.Name), "gemini-3-flash") {
			flashPct = model.Percentage
			break
		}
	}

	// Get Claude (claude-sonnet-4-5, non-thinking)
	claudePct := 0
	for _, model := range quotaFormatted.Models {
		if strings.ToLower(model.Name) == "claude-sonnet-4-5" {
			claudePct = model.Percentage
			break
		}
	}

	overview := fmt.Sprintf("Pro %d%% | Flash %d%% | Claude %d%%", proPct, flashPct, claudePct)
	c.JSON(http.StatusOK, gin.H{"overview": overview})
}

// formatPercentageWithColor formats percentage with ANSI colors
func formatPercentageWithColor(pct int) string {
	const (
		Green = "\033[32m"
		Yellow = "\033[33m"
		Red = "\033[31m"
		Reset = "\033[0m"
	)

	if pct == QuotaFull {
		return Green + "●" + Reset
	} else if pct >= QuotaGood {
		return Green + strconv.Itoa(pct) + "%" + Reset
	} else if pct >= QuotaWarning {
		return Yellow + strconv.Itoa(pct) + "%" + Reset
	} else if pct >= QuotaCritical {
		return Red + strconv.Itoa(pct) + "%" + Reset
	} else {
		return Red + "●" + Reset
	}
}

// formatTimeCompact formats time in compact format
func formatTimeCompact(resetTime string) string {
	if resetTime == "" {
		return ""
	}

	resetDt, err := time.Parse(time.RFC3339, resetTime)
	if err != nil {
		resetDt, err = time.Parse("2006-01-02T15:04:05Z", resetTime)
		if err != nil {
			return ""
		}
	}

	now := time.Now().UTC()
	delta := resetDt.Sub(now)

	if delta <= 0 {
		return ""
	}

	hours := int(delta.Hours())
	minutes := int(delta.Minutes()) % 60

	if hours == 0 && minutes == 0 {
		return ""
	} else if hours == 0 {
		return fmt.Sprintf("%dm", minutes)
	} else if minutes == 0 {
		return fmt.Sprintf("%dh", hours)
	} else {
		return fmt.Sprintf("%dh%dm", hours, minutes)
	}
}

// GetQuotaStatus returns terminal-friendly status
func (s *QuotaService) GetQuotaStatus(c *gin.Context) {
	quotaRaw, err := s.getQuotaData()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	quotaFormatted := formatQuota(quotaRaw, true)

	const (
		Green = "\033[32m"
		Red = "\033[31m"
		Reset = "\033[0m"
		GeminiIcon = "G"
		FlashIcon = "F"
		ClaudeIcon = "󰛄"
	)

	formatModelStatus := func(icon string, pct int, resetTime string) string {
		if pct == QuotaFull {
			return Green + icon + Reset
		} else if pct == 0 {
			return Red + icon + Reset
		} else {
			pctStr := formatPercentageWithColor(pct)
			timeStr := formatTimeCompact(resetTime)
			if timeStr != "" {
				return fmt.Sprintf("%s %s %s", icon, pctStr, timeStr)
			}
			return fmt.Sprintf("%s %s", icon, pctStr)
		}
	}

	// Get Pro (gemini-3-pro-high)
	proPct, proReset := 0, ""
	for _, model := range quotaFormatted.Models {
		if strings.Contains(strings.ToLower(model.Name), "gemini-3-pro-high") {
			proPct = model.Percentage
			proReset = model.ResetTime
			break
		}
	}

	// Get Flash (gemini-3-flash)
	flashPct, flashReset := 0, ""
	for _, model := range quotaFormatted.Models {
		if strings.Contains(strings.ToLower(model.Name), "gemini-3-flash") {
			flashPct = model.Percentage
			flashReset = model.ResetTime
			break
		}
	}

	// Get Claude (claude-sonnet-4-5)
	claudePct, claudeReset := 0, ""
	for _, model := range quotaFormatted.Models {
		if strings.ToLower(model.Name) == "claude-sonnet-4-5" {
			claudePct = model.Percentage
			claudeReset = model.ResetTime
			break
		}
	}

	proStr := formatModelStatus(GeminiIcon, proPct, proReset)
	flashStr := formatModelStatus(FlashIcon, flashPct, flashReset)
	claudeStr := formatModelStatus(ClaudeIcon, claudePct, claudeReset)

	overview := fmt.Sprintf("%s | %s | %s", proStr, flashStr, claudeStr)
	c.JSON(http.StatusOK, gin.H{"overview": overview})
}

// GetAllQuota returns all models with relative reset time
func (s *QuotaService) GetAllQuota(c *gin.Context) {
	quotaRaw, err := s.getQuotaData()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	quotaFormatted := formatQuota(quotaRaw, true)
	c.JSON(http.StatusOK, gin.H{"quota": quotaFormatted})
}

// GetGemini3Pro returns Gemini 3 Pro models
func (s *QuotaService) GetGemini3Pro(c *gin.Context) {
	quotaRaw, err := s.getQuotaData()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	quotaFormatted := formatQuota(quotaRaw, true)
	filtered := filterModels(quotaFormatted, []string{"gemini-3-pro-high", "gemini-3-pro-image", "gemini-3-pro-low"})
	c.JSON(http.StatusOK, gin.H{"quota": filtered})
}

// GetGemini3Flash returns Gemini 3 Flash model
func (s *QuotaService) GetGemini3Flash(c *gin.Context) {
	quotaRaw, err := s.getQuotaData()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	quotaFormatted := formatQuota(quotaRaw, true)
	filtered := filterModels(quotaFormatted, []string{"gemini-3-flash"})
	c.JSON(http.StatusOK, gin.H{"quota": filtered})
}

// GetClaude45 returns Claude 4.5 models
func (s *QuotaService) GetClaude45(c *gin.Context) {
	quotaRaw, err := s.getQuotaData()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	quotaFormatted := formatQuota(quotaRaw, true)
	filtered := filterModels(quotaFormatted, []string{"claude-opus-4-5-thinking", "claude-sonnet-4-5", "claude-sonnet-4-5-thinking"})
	c.JSON(http.StatusOK, gin.H{"quota": filtered})
}
