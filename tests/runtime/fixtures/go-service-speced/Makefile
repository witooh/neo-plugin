.PHONY: test cover build

build:
	go build ./...

test:
	go test ./...

cover:
	go test ./... -coverprofile=coverage.out
	go tool cover -func=coverage.out | tail -1
