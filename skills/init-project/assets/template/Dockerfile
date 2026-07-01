# ================== Stage 1: Builder ==================
FROM public.ecr.aws/docker/library/golang:1.26-alpine AS builder
WORKDIR /app

# Copy go.mod and go.sum to leverage Docker's cache
COPY go.mod go.sum ./

# Copy the rest of the application source code
COPY . .

# CGO_ENABLED=0 disables CGO, creating a statically linked binary
ENV CGO_ENABLED=0 GOOS=linux
RUN go build -mod=vendor -o main ./cmd/api

# ================= Stage 2: Final Image =================
FROM public.ecr.aws/docker/library/alpine:latest
WORKDIR /app

# Copy the compiled binary from the builder stage
COPY --from=builder /app/main .

# Bake the default (local/compose) config into the image. SIT/production override
# every value through environment variables injected from the secret manager.
COPY --from=builder /app/config/config.yaml ./config/config.yaml

# Expose default port
ARG PORT=8080
EXPOSE $PORT

CMD ["./main"]
