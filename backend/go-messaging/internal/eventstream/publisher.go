package eventstream

import (
	"context"
	"encoding/json"
	"time"

	"github.com/redis/go-redis/v9"
)

type Service struct {
	redisClient      *redis.Client
	messagesStreamKey string
	statusStreamKey   string
}

type PendingChatMessage struct {
	Event          string                 `json:"event"`
	ChatUUID       string                 `json:"chat_uuid"`
	SenderUUID     string                 `json:"sender_uuid"`
	SenderEmail    string                 `json:"sender_email"`
	SenderUsername string                 `json:"sender_username"`
	MessageType    string                 `json:"message_type"`
	ClientUUID     string                 `json:"client_uuid"`
	ReplyToUUID    string                 `json:"reply_to_uuid"`
	Text           string                 `json:"text"`
	Payload        map[string]interface{} `json:"payload"`
	SentAt         string                 `json:"sent_at"`
}

type MessageStatusEvent struct {
	Event       string `json:"event"`
	ChatUUID    string `json:"chat_uuid"`
	MessageUUID string `json:"message_uuid"`
	UserUUID    string `json:"user_uuid"`
	DeviceID    string `json:"device_id"`
	SentAt      string `json:"sent_at"`
}

func New(redisClient *redis.Client, messagesStreamKey string, statusStreamKey string) *Service {
	return &Service{
		redisClient:       redisClient,
		messagesStreamKey: messagesStreamKey,
		statusStreamKey:   statusStreamKey,
	}
}

func (s *Service) PublishPendingChatMessage(ctx context.Context, message PendingChatMessage) (string, error) {
	if message.Event == "" {
		message.Event = "pending_save"
	}
	if message.MessageType == "" {
		message.MessageType = "text"
	}
	if message.SentAt == "" {
		message.SentAt = time.Now().UTC().Format(time.RFC3339)
	}

	rawPayload, err := json.Marshal(message)
	if err != nil {
		return "", err
	}

	entryID, err := s.redisClient.XAdd(ctx, &redis.XAddArgs{
		Stream: s.messagesStreamKey,
		Values: map[string]interface{}{
			"event":           message.Event,
			"chat_uuid":       message.ChatUUID,
			"sender_uuid":     message.SenderUUID,
			"sender_email":    message.SenderEmail,
			"sender_username": message.SenderUsername,
			"message_type":    message.MessageType,
			"client_uuid":     message.ClientUUID,
			"reply_to_uuid":   message.ReplyToUUID,
			"text":            message.Text,
			"sent_at":         message.SentAt,
			"payload":         string(rawPayload),
		},
	}).Result()
	if err != nil {
		return "", err
	}

	return entryID, nil
}

func (s *Service) PublishMessageStatusEvent(ctx context.Context, event MessageStatusEvent) (string, error) {
	if event.Event == "" {
		event.Event = "delivered"
	}
	if event.SentAt == "" {
		event.SentAt = time.Now().UTC().Format(time.RFC3339)
	}

	rawPayload, err := json.Marshal(event)
	if err != nil {
		return "", err
	}

	entryID, err := s.redisClient.XAdd(ctx, &redis.XAddArgs{
		Stream: s.statusStreamKey,
		Values: map[string]interface{}{
			"event":        event.Event,
			"chat_uuid":    event.ChatUUID,
			"message_uuid": event.MessageUUID,
			"user_uuid":    event.UserUUID,
			"device_id":    event.DeviceID,
			"sent_at":      event.SentAt,
			"payload":      string(rawPayload),
		},
	}).Result()
	if err != nil {
		return "", err
	}

	return entryID, nil
}