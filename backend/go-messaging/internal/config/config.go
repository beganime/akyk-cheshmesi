package config

import (
	"log"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/joho/godotenv"
)

type Config struct {
	AppEnv                  string
	HTTPHost                string
	HTTPPort                string
	JWTSecret               string
	RedisCacheURL           string
	RedisStreamURL          string
	StreamMessagesKey       string
	StreamMessageStatusKey  string
	RealtimeEventsChannel   string
	PresenceTTLSeconds      int
	WebSocketReadLimit      int64
	WebSocketWriteBuffer    int
	RateLimitMessagesPer10s int
	RateLimitTypingPer10s   int
	RateLimitStatusesPer10s int

	CallSTUNURLs               []string
	CallTURNURLs               []string
	CallTURNUsername           string
	CallTURNCredential         string
	CallMaxPeersPerRoom        int
	CallCleanupIntervalSeconds int
	CallEmptyRoomTTLSeconds    int
	CallWSReadLimit            int64
}

func Load() Config {
	loadDotEnv()

	cfg := Config{
		AppEnv:                   getEnv("GO_ENV", "development"),
		HTTPHost:                 getEnv("GO_HTTP_HOST", "0.0.0.0"),
		HTTPPort:                 getEnv("GO_HTTP_PORT", "8081"),
		JWTSecret:                getEnv("GO_JWT_SECRET", getEnv("JWT_SECRET", "")),
		RedisCacheURL:            firstNonEmpty("GO_REDIS_CACHE_URL", "GO_REDIS_URL", "REDIS_CACHE_URL", "redis://127.0.0.1:6379/0"),
		RedisStreamURL:           firstNonEmpty("GO_REDIS_STREAM_URL", "REDIS_STREAM_URL", "", "redis://127.0.0.1:6379/1"),
		StreamMessagesKey:        getEnv("REDIS_STREAM_MESSAGES_KEY", "stream:messages"),
		StreamMessageStatusKey:   getEnv("REDIS_STREAM_MESSAGE_STATUS_KEY", "stream:message-statuses"),
		RealtimeEventsChannel:    getEnv("REDIS_REALTIME_EVENTS_CHANNEL", "realtime:events"),
		PresenceTTLSeconds:       getEnvInt("REDIS_PRESENCE_TTL_SECONDS", 90),
		WebSocketReadLimit:       getEnvInt64("GO_WS_READ_LIMIT", 8192),
		WebSocketWriteBuffer:     getEnvInt("GO_WS_WRITE_BUFFER", 256),
		RateLimitMessagesPer10s:  getEnvInt("GO_RATE_LIMIT_MESSAGES_PER_10S", 12),
		RateLimitTypingPer10s:    getEnvInt("GO_RATE_LIMIT_TYPING_PER_10S", 30),
		RateLimitStatusesPer10s:  getEnvInt("GO_RATE_LIMIT_STATUSES_PER_10S", 40),

		CallSTUNURLs:               getEnvCSV("GO_CALL_STUN_URLS", []string{"stun:stun.l.google.com:19302", "stun:stun1.l.google.com:19302"}),
		CallTURNURLs:               getEnvCSV("GO_CALL_TURN_URLS", nil),
		CallTURNUsername:           getEnv("GO_CALL_TURN_USERNAME", ""),
		CallTURNCredential:         getEnv("GO_CALL_TURN_CREDENTIAL", ""),
		CallMaxPeersPerRoom:        getEnvInt("GO_CALL_MAX_PEERS_PER_ROOM", 8),
		CallCleanupIntervalSeconds: getEnvInt("GO_CALL_CLEANUP_INTERVAL_SECONDS", 15),
		CallEmptyRoomTTLSeconds:    getEnvInt("GO_CALL_EMPTY_ROOM_TTL_SECONDS", 30),
		CallWSReadLimit:            getEnvInt64("GO_CALL_WS_READ_LIMIT", 65536),
	}

	log.Printf(
		"config loaded | env=%s addr=%s:%s cache=%s stream=%s jwt_set=%t stun=%d turn=%d max_room_peers=%d",
		cfg.AppEnv,
		cfg.HTTPHost,
		cfg.HTTPPort,
		cfg.RedisCacheURL,
		cfg.RedisStreamURL,
		cfg.JWTSecret != "",
		len(cfg.CallSTUNURLs),
		len(cfg.CallTURNURLs),
		cfg.CallMaxPeersPerRoom,
	)

	return cfg
}

func loadDotEnv() {
	candidates := []string{
		".env",
		filepath.Join("..", ".env"),
		filepath.Join("..", "..", ".env"),
		filepath.Join("..", "..", "..", ".env"),
	}

	for _, candidate := range candidates {
		if _, err := os.Stat(candidate); err == nil {
			if err := godotenv.Load(candidate); err != nil {
				log.Printf("found .env but failed to load: %s | error: %v", candidate, err)
				return
			}
			log.Printf(".env loaded from: %s", candidate)
			return
		}
	}

	log.Printf("no .env file found in known locations")
}

func (c Config) Addr() string {
	return c.HTTPHost + ":" + c.HTTPPort
}

func getEnv(key string, fallback string) string {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}
	return value
}

func firstNonEmpty(primary string, secondary string, tertiary string, fallback string) string {
	for _, key := range []string{primary, secondary, tertiary} {
		if key == "" {
			continue
		}
		if value := os.Getenv(key); value != "" {
			return value
		}
	}
	return fallback
}

func getEnvInt(key string, fallback int) int {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}

	parsed, err := strconv.Atoi(value)
	if err != nil {
		return fallback
	}
	return parsed
}

func getEnvInt64(key string, fallback int64) int64 {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}

	parsed, err := strconv.ParseInt(value, 10, 64)
	if err != nil {
		return fallback
	}
	return parsed
}

func getEnvCSV(key string, fallback []string) []string {
	raw := strings.TrimSpace(os.Getenv(key))
	if raw == "" {
		if fallback == nil {
			return nil
		}
		out := make([]string, len(fallback))
		copy(out, fallback)
		return out
	}

	parts := strings.Split(raw, ",")
	result := make([]string, 0, len(parts))
	for _, part := range parts {
		value := strings.TrimSpace(part)
		if value != "" {
			result = append(result, value)
		}
	}

	if len(result) == 0 && fallback != nil {
		out := make([]string, len(fallback))
		copy(out, fallback)
		return out
	}

	return result
}