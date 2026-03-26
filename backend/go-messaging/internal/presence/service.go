package presence

import (
	"context"
	"encoding/json"
	"time"

	"github.com/redis/go-redis/v9"
)

type Service struct {
	redisClient *redis.Client
	ttl         time.Duration
}

type Payload struct {
	UserUUID        string `json:"user_uuid"`
	Email           string `json:"email"`
	Username        string `json:"username"`
	Status          string `json:"status"`
	ConnectionCount int    `json:"connection_count"`
	LastSeenAt      string `json:"last_seen_at"`
}

func New(redisClient *redis.Client, ttlSeconds int) *Service {
	return &Service{
		redisClient: redisClient,
		ttl:         time.Duration(ttlSeconds) * time.Second,
	}
}

func (s *Service) key(userUUID string) string {
	return "presence:" + userUUID
}

func (s *Service) SetOnline(ctx context.Context, userUUID, email, username string, connectionCount int) error {
	payload := Payload{
		UserUUID:        userUUID,
		Email:           email,
		Username:        username,
		Status:          "online",
		ConnectionCount: connectionCount,
		LastSeenAt:      time.Now().UTC().Format(time.RFC3339),
	}

	raw, err := json.Marshal(payload)
	if err != nil {
		return err
	}

	return s.redisClient.Set(ctx, s.key(userUUID), raw, s.ttl).Err()
}

func (s *Service) SetOffline(ctx context.Context, userUUID, email, username string) error {
	payload := Payload{
		UserUUID:        userUUID,
		Email:           email,
		Username:        username,
		Status:          "offline",
		ConnectionCount: 0,
		LastSeenAt:      time.Now().UTC().Format(time.RFC3339),
	}

	raw, err := json.Marshal(payload)
	if err != nil {
		return err
	}

	return s.redisClient.Set(ctx, s.key(userUUID), raw, s.ttl).Err()
}