package ratelimit

import (
	"context"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
)

type Service struct {
	redisClient *redis.Client
	namespace   string
}

func New(redisClient *redis.Client, namespace string) *Service {
	if namespace == "" {
		namespace = "ratelimit"
	}

	return &Service{
		redisClient: redisClient,
		namespace:   namespace,
	}
}

func (s *Service) key(bucket string, subject string) string {
	return fmt.Sprintf("%s:%s:%s", s.namespace, bucket, subject)
}

func (s *Service) Allow(ctx context.Context, bucket string, subject string, limit int, window time.Duration) (bool, int64, error) {
	key := s.key(bucket, subject)

	pipe := s.redisClient.TxPipeline()
	incr := pipe.Incr(ctx, key)
	ttl := pipe.TTL(ctx, key)

	_, err := pipe.Exec(ctx)
	if err != nil {
		return false, 0, err
	}

	current := incr.Val()

	if ttl.Val() < 0 {
		if err := s.redisClient.Expire(ctx, key, window).Err(); err != nil {
			return false, 0, err
		}
	}

	remainingTTL := s.redisClient.TTL(ctx, key).Val()
	if remainingTTL < 0 {
		remainingTTL = window
	}

	if int(current) > limit {
		return false, int64(remainingTTL.Seconds()), nil
	}

	return true, int64(remainingTTL.Seconds()), nil
}