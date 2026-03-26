package main

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"time"
	
	"akyl-chesmesi/go-messaging/internal/ratelimit"
	"akyl-chesmesi/go-messaging/internal/auth"
	"akyl-chesmesi/go-messaging/internal/chataccess"
	"akyl-chesmesi/go-messaging/internal/config"
	"akyl-chesmesi/go-messaging/internal/eventstream"
	"akyl-chesmesi/go-messaging/internal/presence"
	"akyl-chesmesi/go-messaging/internal/realtime"
	"akyl-chesmesi/go-messaging/internal/redisx"
	"akyl-chesmesi/go-messaging/internal/ws"

	"github.com/gorilla/websocket"
)

type healthResponse struct {
	Status  string `json:"status"`
	Service string `json:"service"`
	App     string `json:"app"`
}

func main() {
	cfg := config.Load()

	if cfg.JWTSecret == "" {
		log.Fatal("GO_JWT_SECRET/JWT_SECRET is empty")
	}

	cacheRedis, err := redisx.NewClient(cfg.RedisCacheURL)
	if err != nil {
		log.Fatalf("cache redis connect failed: %v", err)
	}

	streamRedis, err := redisx.NewClient(cfg.RedisStreamURL)
	if err != nil {
		log.Fatalf("stream redis connect failed: %v", err)
	}

	presenceService := presence.New(cacheRedis, cfg.PresenceTTLSeconds)
	accessService := chataccess.New(cacheRedis)
	streamService := eventstream.New(
		streamRedis,
		cfg.StreamMessagesKey,
		cfg.StreamMessageStatusKey,
	)

	rateLimiter := ratelimit.New(cacheRedis, "go:ratelimit")

	hub := ws.NewHub(
		presenceService,
		accessService,
		streamService,
		rateLimiter,
		cfg.RateLimitMessagesPer10s,
		cfg.RateLimitTypingPer10s,
		cfg.RateLimitStatusesPer10s,
	)
	
	realtimeSubscriber := realtime.New(streamRedis, cfg.RealtimeEventsChannel, hub)
	go realtimeSubscriber.Start(context.Background())

	mux := http.NewServeMux()
	mux.HandleFunc("/healthz", healthHandler)
	mux.HandleFunc("/ws", serveWS(cfg, hub))

	server := &http.Server{
		Addr:              cfg.Addr(),
		Handler:           loggingMiddleware(mux),
		ReadHeaderTimeout: 5 * time.Second,
		IdleTimeout:       60 * time.Second,
	}

	log.Printf("go-messaging is running on %s", cfg.Addr())
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("server failed: %v", err)
	}
}

func serveWS(cfg config.Config, hub *ws.Hub) http.HandlerFunc {
	upgrader := websocket.Upgrader{
		ReadBufferSize:  1024,
		WriteBufferSize: 1024,
		CheckOrigin: func(r *http.Request) bool {
			return true
		},
	}

	return func(w http.ResponseWriter, r *http.Request) {
		tokenString := auth.ExtractTokenFromRequest(r)
		claims, err := auth.ValidateAccessToken(tokenString, cfg.JWTSecret)
		if err != nil {
			log.Printf("websocket auth failed: %v", err)
			http.Error(w, "unauthorized websocket: "+err.Error(), http.StatusUnauthorized)
			return
		}

		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			log.Printf("websocket upgrade failed: %v", err)
			return
		}

		client := ws.NewClient(
			hub,
			conn,
			claims.UserUUID,
			claims.Email,
			claims.Username,
			cfg.WebSocketWriteBuffer,
		)

		hub.Register(client)

		client.Send <- mustJSON(ws.OutgoingMessage{
			Type: "connected",
			Payload: map[string]interface{}{
				"user_uuid": claims.UserUUID,
				"email":     claims.Email,
				"username":  claims.Username,
				"ts":        time.Now().UTC().Format(time.RFC3339),
			},
		})

		go client.WritePump()
		client.ReadPump(cfg.WebSocketReadLimit)
	}
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)

	resp := healthResponse{
		Status:  "ok",
		Service: "go-messaging",
		App:     "akyl-chesmesi",
	}

	_ = json.NewEncoder(w).Encode(resp)
}

func loggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		startedAt := time.Now()
		next.ServeHTTP(w, r)
		log.Printf("%s %s %s", r.Method, r.URL.Path, time.Since(startedAt))
	})
}

func mustJSON(message ws.OutgoingMessage) []byte {
	payload, err := json.Marshal(message)
	if err != nil {
		return []byte(`{"type":"error","payload":{"detail":"marshal failed"}}`)
	}
	return payload
}