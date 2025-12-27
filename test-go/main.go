package main

import (
	"log"
	"os"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
)

func main() {
	// Load .env file
	if err := godotenv.Load("../.env"); err != nil {
		log.Printf("Warning: .env file not found: %v", err)
	}

	// Get port from environment
	port := os.Getenv("PORT")
	if port == "" {
		port = "8000"
	}

	// Validate port
	if _, err := strconv.Atoi(port); err != nil {
		log.Fatalf("Invalid PORT value: %s", port)
	}

	// Create Gin router
	r := gin.Default()

	// Setup routes
	setupRoutes(r)

	// Start server
	log.Printf("Starting server on port %s", port)
	if err := r.Run(":" + port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
