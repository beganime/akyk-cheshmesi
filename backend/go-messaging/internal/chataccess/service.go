package chataccess

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/redis/go-redis/v9"
)

type Membership struct {
	ChatUUID        string `json:"chat_uuid"`
	UserUUID        string `json:"user_uuid"`
	Role            string `json:"role"`
	IsActive        bool   `json:"is_active"`
	IsMuted         bool   `json:"is_muted"`
	CanSendMessages bool   `json:"can_send_messages"`
	LastReadAt      string `json:"last_read_at"`
	JoinedAt        string `json:"joined_at"`
}

type Service struct {
	redisClient *redis.Client
}

func New(redisClient *redis.Client) *Service {
	return &Service{redisClient: redisClient}
}

func (s *Service) membershipKey(chatUUID string, userUUID string) string {
	return fmt.Sprintf("chat:member:%s:%s", chatUUID, userUUID)
}

func (s *Service) GetMembership(ctx context.Context, chatUUID string, userUUID string) (*Membership, error) {
	raw, err := s.redisClient.Get(ctx, s.membershipKey(chatUUID, userUUID)).Result()
	if err == redis.Nil {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}

	var membership Membership
	if err := json.Unmarshal([]byte(raw), &membership); err != nil {
		return nil, err
	}

	return &membership, nil
}

func (s *Service) CanAccessChat(ctx context.Context, chatUUID string, userUUID string) (bool, *Membership, error) {
	membership, err := s.GetMembership(ctx, chatUUID, userUUID)
	if err != nil {
		return false, nil, err
	}
	if membership == nil {
		return false, nil, nil
	}
	if !membership.IsActive {
		return false, membership, nil
	}
	return true, membership, nil
}

func (s *Service) CanSendInChat(ctx context.Context, chatUUID string, userUUID string) (bool, *Membership, error) {
	membership, err := s.GetMembership(ctx, chatUUID, userUUID)
	if err != nil {
		return false, nil, err
	}
	if membership == nil {
		return false, nil, nil
	}
	if !membership.IsActive || !membership.CanSendMessages {
		return false, membership, nil
	}
	return true, membership, nil
}