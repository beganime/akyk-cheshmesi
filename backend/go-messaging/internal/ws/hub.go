package ws

import (
	"context"
	"encoding/json"
	"errors"
	"log"
	"sync"
	"time"

	"akyl-chesmesi/go-messaging/internal/chataccess"
	"akyl-chesmesi/go-messaging/internal/eventstream"
	"akyl-chesmesi/go-messaging/internal/presence"
	"akyl-chesmesi/go-messaging/internal/ratelimit"
)

type Hub struct {
	mu                 sync.RWMutex
	users              map[string]map[*Client]struct{}
	chats              map[string]map[*Client]struct{}
	callRooms          map[string]map[*Client]struct{}
	presence           *presence.Service
	access             *chataccess.Service
	stream             *eventstream.Service
	rateLimiter        *ratelimit.Service
	messageLimit10s    int
	typingLimit10s     int
	statusLimit10s     int
}

func NewHub(
	presenceService *presence.Service,
	accessService *chataccess.Service,
	streamService *eventstream.Service,
	rateLimiter *ratelimit.Service,
	messageLimit10s int,
	typingLimit10s int,
	statusLimit10s int,
) *Hub {
	return &Hub{
		users:           make(map[string]map[*Client]struct{}),
		chats:           make(map[string]map[*Client]struct{}),
		callRooms:       make(map[string]map[*Client]struct{}),
		presence:        presenceService,
		access:          accessService,
		stream:          streamService,
		rateLimiter:     rateLimiter,
		messageLimit10s: messageLimit10s,
		typingLimit10s:  typingLimit10s,
		statusLimit10s:  statusLimit10s,
	}
}

func (h *Hub) Register(client *Client) {
	h.mu.Lock()
	if _, ok := h.users[client.UserUUID]; !ok {
		h.users[client.UserUUID] = make(map[*Client]struct{})
	}
	h.users[client.UserUUID][client] = struct{}{}
	connectionCount := len(h.users[client.UserUUID])
	h.mu.Unlock()

	if h.presence != nil {
		if err := h.presence.SetOnline(
			context.Background(),
			client.UserUUID,
			client.Email,
			client.Username,
			connectionCount,
		); err != nil {
			log.Printf("presence set online failed: %v", err)
		}
	}
}

func (h *Hub) Unregister(client *Client) {
	h.mu.Lock()

	if userClients, ok := h.users[client.UserUUID]; ok {
		delete(userClients, client)
		if len(userClients) == 0 {
			delete(h.users, client.UserUUID)
		}
	}

	for chatUUID := range client.subscriptions {
		if chatClients, ok := h.chats[chatUUID]; ok {
			delete(chatClients, client)
			if len(chatClients) == 0 {
				delete(h.chats, chatUUID)
			}
		}
	}

	for roomKey := range client.callRooms {
		if roomClients, ok := h.callRooms[roomKey]; ok {
			delete(roomClients, client)
			if len(roomClients) == 0 {
				delete(h.callRooms, roomKey)
			}
		}
	}

	select {
	case <-client.closed:
	default:
		close(client.closed)
		close(client.Send)
	}

	connectionCount := 0
	if userClients, ok := h.users[client.UserUUID]; ok {
		connectionCount = len(userClients)
	}

	h.mu.Unlock()

	if h.presence != nil {
		var err error
		if connectionCount > 0 {
			err = h.presence.SetOnline(
				context.Background(),
				client.UserUUID,
				client.Email,
				client.Username,
				connectionCount,
			)
		} else {
			err = h.presence.SetOffline(
				context.Background(),
				client.UserUUID,
				client.Email,
				client.Username,
			)
		}
		if err != nil {
			log.Printf("presence update failed: %v", err)
		}
	}
}

func (h *Hub) Subscribe(client *Client, chatUUID string) {
	if chatUUID == "" {
		return
	}

	h.mu.Lock()
	defer h.mu.Unlock()

	if _, ok := h.chats[chatUUID]; !ok {
		h.chats[chatUUID] = make(map[*Client]struct{})
	}
	h.chats[chatUUID][client] = struct{}{}
	client.subscriptions[chatUUID] = struct{}{}
}

func (h *Hub) Unsubscribe(client *Client, chatUUID string) {
	if chatUUID == "" {
		return
	}

	h.mu.Lock()
	defer h.mu.Unlock()

	if chatClients, ok := h.chats[chatUUID]; ok {
		delete(chatClients, client)
		if len(chatClients) == 0 {
			delete(h.chats, chatUUID)
		}
	}

	delete(client.subscriptions, chatUUID)
}

func (h *Hub) IsSubscribed(client *Client, chatUUID string) bool {
	h.mu.RLock()
	defer h.mu.RUnlock()

	_, ok := client.subscriptions[chatUUID]
	return ok
}

func (h *Hub) CanAccessChat(ctx context.Context, chatUUID string, userUUID string) (bool, *chataccess.Membership, error) {
	if h.access == nil {
		return false, nil, errors.New("chat access service is not configured")
	}
	return h.access.CanAccessChat(ctx, chatUUID, userUUID)
}

func (h *Hub) CanSendInChat(ctx context.Context, chatUUID string, userUUID string) (bool, *chataccess.Membership, error) {
	if h.access == nil {
		return false, nil, errors.New("chat access service is not configured")
	}
	return h.access.CanSendInChat(ctx, chatUUID, userUUID)
}

func (h *Hub) PublishPendingChatMessage(ctx context.Context, message eventstream.PendingChatMessage) (string, error) {
	if h.stream == nil {
		return "", errors.New("stream service is not configured")
	}
	return h.stream.PublishPendingChatMessage(ctx, message)
}

func (h *Hub) PublishMessageStatusEvent(ctx context.Context, event eventstream.MessageStatusEvent) (string, error) {
	if h.stream == nil {
		return "", errors.New("stream service is not configured")
	}
	return h.stream.PublishMessageStatusEvent(ctx, event)
}

func (h *Hub) BroadcastToChat(chatUUID string, message OutgoingMessage) {
	if chatUUID == "" {
		return
	}

	payload, err := json.Marshal(message)
	if err != nil {
		log.Printf("broadcast marshal failed: %v", err)
		return
	}

	h.mu.RLock()
	targetsMap := h.chats[chatUUID]
	targets := make([]*Client, 0, len(targetsMap))
	for client := range targetsMap {
		targets = append(targets, client)
	}
	h.mu.RUnlock()

	staleClients := make([]*Client, 0)

	for _, client := range targets {
		select {
		case client.Send <- payload:
		default:
			staleClients = append(staleClients, client)
		}
	}

	for _, client := range staleClients {
		h.Unregister(client)
	}
}

func (h *Hub) JoinCallRoom(client *Client, roomKey string) []string {
	if roomKey == "" {
		return []string{}
	}

	h.mu.Lock()
	defer h.mu.Unlock()

	if _, ok := h.callRooms[roomKey]; !ok {
		h.callRooms[roomKey] = make(map[*Client]struct{})
	}

	existingPeers := make([]string, 0, len(h.callRooms[roomKey]))
	for peer := range h.callRooms[roomKey] {
		if peer != client && peer.PeerID != "" {
			existingPeers = append(existingPeers, peer.PeerID)
		}
	}

	h.callRooms[roomKey][client] = struct{}{}
	client.callRooms[roomKey] = struct{}{}

	return existingPeers
}

func (h *Hub) LeaveCallRoom(client *Client, roomKey string) {
	if roomKey == "" {
		return
	}

	h.mu.Lock()
	defer h.mu.Unlock()

	if roomClients, ok := h.callRooms[roomKey]; ok {
		delete(roomClients, client)
		if len(roomClients) == 0 {
			delete(h.callRooms, roomKey)
		}
	}

	delete(client.callRooms, roomKey)
}

func (h *Hub) IsInCallRoom(client *Client, roomKey string) bool {
	if roomKey == "" {
		return false
	}

	h.mu.RLock()
	defer h.mu.RUnlock()

	_, ok := client.callRooms[roomKey]
	return ok
}

func (h *Hub) BroadcastToCallRoom(roomKey string, sender *Client, message OutgoingMessage) {
	if roomKey == "" {
		return
	}

	payload, err := json.Marshal(message)
	if err != nil {
		log.Printf("call broadcast marshal failed: %v", err)
		return
	}

	h.mu.RLock()
	roomClients := h.callRooms[roomKey]
	targets := make([]*Client, 0, len(roomClients))
	for client := range roomClients {
		if client != sender {
			targets = append(targets, client)
		}
	}
	h.mu.RUnlock()

	staleClients := make([]*Client, 0)

	for _, client := range targets {
		select {
		case client.Send <- payload:
		default:
			staleClients = append(staleClients, client)
		}
	}

	for _, client := range staleClients {
		h.Unregister(client)
	}
}

func (h *Hub) AllowMessage(ctx context.Context, userUUID string) (bool, int64, error) {
	if h.rateLimiter == nil {
		return true, 0, nil
	}
	return h.rateLimiter.Allow(ctx, "messages_10s", userUUID, h.messageLimit10s, 10*time.Second)
}

func (h *Hub) AllowTyping(ctx context.Context, userUUID string) (bool, int64, error) {
	if h.rateLimiter == nil {
		return true, 0, nil
	}
	return h.rateLimiter.Allow(ctx, "typing_10s", userUUID, h.typingLimit10s, 10*time.Second)
}

func (h *Hub) AllowStatus(ctx context.Context, userUUID string) (bool, int64, error) {
	if h.rateLimiter == nil {
		return true, 0, nil
	}
	return h.rateLimiter.Allow(ctx, "statuses_10s", userUUID, h.statusLimit10s, 10*time.Second)
}