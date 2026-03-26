FROM golang:1.22-alpine AS builder
WORKDIR /src
RUN apk add --no-cache git ca-certificates
COPY backend/go-messaging/go.mod backend/go-messaging/go.sum* ./backend/go-messaging/
WORKDIR /src/backend/go-messaging
RUN go mod download || true
WORKDIR /src
COPY . /src
WORKDIR /src/backend/go-messaging
RUN go mod tidy && CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o /out/go-messaging ./cmd/server

FROM alpine:3.20
RUN addgroup -S app && adduser -S app -G app && apk add --no-cache ca-certificates tzdata
WORKDIR /app
COPY --from=builder /out/go-messaging /usr/local/bin/go-messaging
USER app
EXPOSE 8081
CMD ["/usr/local/bin/go-messaging"]
