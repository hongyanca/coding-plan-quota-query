# syntax=docker/dockerfile:1

# ============================================
# Stage 1: Build stage
# ============================================
FROM golang:1.25-trixie AS builder

# Security: Create non-root user for build
RUN groupadd --gid 1000 buildgroup && \
    useradd --uid 1000 --gid 1000 --shell /bin/false builduser

WORKDIR /app

# Copy go mod files first (better layer caching)
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download && go mod verify

# Copy source code
COPY *.go ./

# Build the application with security flags
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -ldflags='-w -s -extldflags "-static"' \
    -a -installsuffix cgo \
    -o main .

# ============================================
# Stage 2: Runtime stage - minimal final image
# ============================================
FROM gcr.io/distroless/static-debian12:nonroot

# Set working directory
WORKDIR /app

# Copy the binary from builder stage
COPY --from=builder /app/main /app/main

# Security: Use distroless nonroot user (uid 65532)
USER nonroot:nonroot

# Expose port
EXPOSE 8000

# Health check (distroless doesn't have curl, so we rely on external monitoring)
# HEALTHCHECK is handled by orchestrator (k8s, docker-compose, etc.)

# Run the application
ENTRYPOINT ["/app/main"]
