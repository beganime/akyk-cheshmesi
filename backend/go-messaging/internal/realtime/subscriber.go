package realtime

import (
	"context"
	"encoding/json"
	"log"

	"akyl-chesmesi/go-messaging/internal/ws"

	"github.com/redis/go-redis/v9"
)

type Envelope struct {
	Type     string                 `json:"type"`
	ChatUUID string                 `json:"chat_uuid"`
	Payload  map[string]interface{} `json:"payload"`
}

type Subscriber struct {
	redisClient *redis.Client
	channel     string
	hub         *ws.Hub
}

func New(redisClient *redis.Client, channel string, hub *ws.Hub) *Subscriber {
	return &Subscriber{
		redisClient: redisClient,
		channel:     channel,
		hub:         hub,
	}
}

func (s *Subscriber) Start(ctx context.Context) {
	pubsub := s.redisClient.Subscribe(ctx, s.channel)
	defer pubsub.Close()

	_, err := pubsub.Receive(ctx)
	if err != nil {
		log.Printf("realtime pubsub subscribe failed: %v", err)
		return
	}

	log.Printf("realtime pubsub subscribed to channel: %s", s.channel)

	ch := pubsub.Channel()

	for {
		select {
		case <-ctx.Done():
			log.Printf("realtime pubsub stopped")
			return

		case msg, ok := <-ch:
			if !ok {
				log.Printf("realtime pubsub channel closed")
				return
			}

			var envelope Envelope
			if err := json.Unmarshal([]byte(msg.Payload), &envelope); err != nil {
				log.Printf("invalid realtime envelope: %v", err)
				continue
			}

			if envelope.ChatUUID == "" || envelope.Type == "" {
				continue
			}

			s.hub.BroadcastToChat(envelope.ChatUUID, ws.OutgoingMessage{
				Type:     envelope.Type,
				ChatUUID: envelope.ChatUUID,
				Payload:  envelope.Payload,
			})
		}
	}
}