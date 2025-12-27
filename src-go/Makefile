.PHONY: build run test clean deps

# Build the application
build:
	go build -o bin/antigravity-quota .

# Run the application
run:
	go run .

# Run tests
test:
	cd ../test-go && go test -v

# Clean build artifacts
clean:
	rm -rf bin/

# Download dependencies
deps:
	go mod tidy
	go mod download

# Run with race detection
run-race:
	go run -race .

# Build for multiple platforms
build-all:
	GOOS=linux GOARCH=amd64 go build -o bin/antigravity-quota-linux-amd64 .
	GOOS=darwin GOARCH=amd64 go build -o bin/antigravity-quota-darwin-amd64 .
	GOOS=darwin GOARCH=arm64 go build -o bin/antigravity-quota-darwin-arm64 .
	GOOS=windows GOARCH=amd64 go build -o bin/antigravity-quota-windows-amd64.exe .

# Format code
fmt:
	go fmt ./...

# Lint code (requires golangci-lint)
lint:
	golangci-lint run

# Run benchmarks
bench:
	cd ../test-go && go test -bench=.

# Install development tools
install-tools:
	go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
