package ws

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"strings"
	"time"

	"akyl-chesmesi/go-messaging/internal/eventstream"

	"github.com/gorilla/websocket"
)

const (
	writeWait      = 10 * time.Second
	pongWait       = 60 * time.Second
	pingPeriod     = (pongWait * 9) / 10
	maxMessageSize = 8192
)

type Client struct {
	Hub           *Hub
	Conn          *websocket.Conn
	Send          chan []byte
	UserUUID      string
	Email         string
	Username      string
	PeerID        string
	subscriptions map[string]struct{}
	callRooms     map[string]struct{}
	closed        chan struct{}
}

func NewClient(hub *Hub, conn *websocket.Conn, userUUID, email, username string, writeBuffer int) *Client {
	if writeBuffer <= 0 {
		writeBuffer = 256
	}

	return &Client{
		Hub:           hub,
		Conn:          conn,
		Send:          make(chan []byte, writeBuffer),
		UserUUID:      userUUID,
		Email:         email,
		Username:      username,
		PeerID:        fmt.Sprintf("%s-%d", userUUID, time.Now().UnixNano()),
		subscriptions: make(map[string]struct{}),
		callRooms:     make(map[string]struct{}),
		closed:        make(chan struct{}),
	}
}

func (c *Client) ReadPump(readLimit int64) {
	defer func() {
		c.Hub.Unregister(c)
		_ = c.Conn.Close()
	}()

	if readLimit <= 0 {
		readLimit = maxMessageSize
	}

	c.Conn.SetReadLimit(readLimit)
	_ = c.Conn.SetReadDeadline(time.Now().Add(pongWait))
	c.Conn.SetPongHandler(func(string) error {
		return c.Conn.SetReadDeadline(time.Now().Add(pongWait))
	})

	for {
		_, message, err := c.Conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Printf("websocket read error: %v", err)
			}
			break
		}

		c.handleIncoming(message)
	}
}

func (c *Client) WritePump() {
	ticker := time.NewTicker(pingPeriod)
	defer func() {
		ticker.Stop()
		_ = c.Conn.Close()
	}()

	for {
		select {
		case message, ok := <-c.Send:
			_ = c.Conn.SetWriteDeadline(time.Now().Add(writeWait))
			if !ok {
				_ = c.Conn.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}

			writer, err := c.Conn.NextWriter(websocket.TextMessage)
			if err != nil {
				return
			}

			if _, err := writer.Write(message); err != nil {
				_ = writer.Close()
				return
			}

			if err := writer.Close(); err != nil {
				return
			}

		case <-ticker.C:
			_ = c.Conn.SetWriteDeadline(time.Now().Add(writeWait))
			if err := c.Conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}

		case <-c.closed:
			return
		}
	}
}

func (c *Client) handleIncoming(raw []byte) {
	var incoming IncomingMessage
	if err := json.Unmarshal(raw, &incoming); err != nil {
		c.sendJSON(OutgoingMessage{
			Type: "error",
			Payload: map[string]interface{}{
				"detail": "invalid JSON payload",
			},
		})
		return
	}

	switch incoming.Type {
	case "ping":
		c.sendJSON(OutgoingMessage{
			Type: "pong",
			Payload: map[string]interface{}{
				"ts": time.Now().UTC().Format(time.RFC3339),
			},
		})

	case "whoami":
		c.sendJSON(OutgoingMessage{
			Type: "whoami",
			Payload: map[string]interface{}{
				"user_uuid": c.UserUUID,
				"email":     c.Email,
				"username":  c.Username,
				"peer_id":   c.PeerID,
			},
		})

	case "subscribe_chat":
		if incoming.ChatUUID == "" {
			c.sendError("chat_uuid is required")
			return
		}

		allowed, membership, err := c.Hub.CanAccessChat(context.Background(), incoming.ChatUUID, c.UserUUID)
		if err != nil {
			log.Printf("subscribe chat access check failed: %v", err)
			c.sendError("chat access check failed")
			return
		}
		if !allowed {
			c.sendError("you are not a member of this chat")
			return
		}

		c.Hub.Subscribe(c, incoming.ChatUUID)
		c.sendJSON(OutgoingMessage{
			Type:     "subscribed",
			ChatUUID: incoming.ChatUUID,
			Payload: map[string]interface{}{
				"detail":            "subscribed successfully",
				"role":              membership.Role,
				"can_send_messages": membership.CanSendMessages,
			},
		})

	case "unsubscribe_chat":
		if incoming.ChatUUID == "" {
			c.sendError("chat_uuid is required")
			return
		}

		c.Hub.Unsubscribe(c, incoming.ChatUUID)
		c.sendJSON(OutgoingMessage{
			Type:     "unsubscribed",
			ChatUUID: incoming.ChatUUID,
			Payload: map[string]interface{}{
				"detail": "unsubscribed successfully",
			},
		})

	case "typing_start", "typing_stop":
		if incoming.ChatUUID == "" {
			c.sendError("chat_uuid is required")
			return
		}
		allowedRate, retryAfter, err := c.Hub.AllowTyping(context.Background(), c.UserUUID)
		if err != nil {
			log.Printf("typing rate limit check failed: %v", err)
			c.sendError("typing rate limit check failed")
			return
		}
		if !allowedRate {
			c.sendJSON(OutgoingMessage{
				Type: "rate_limited",
				Payload: map[string]interface{}{
					"scope":               "typing",
					"retry_after_seconds": retryAfter,
				},
			})
			return
		}
		if !c.Hub.IsSubscribed(c, incoming.ChatUUID) {
			c.sendError("subscribe to chat first")
			return
		}

		allowed, _, err := c.Hub.CanAccessChat(context.Background(), incoming.ChatUUID, c.UserUUID)
		if err != nil {
			log.Printf("typing chat access check failed: %v", err)
			c.sendError("typing permission check failed")
			return
		}
		if !allowed {
			c.sendError("you are not a member of this chat")
			return
		}

		c.Hub.BroadcastToChat(incoming.ChatUUID, OutgoingMessage{
			Type:     incoming.Type,
			ChatUUID: incoming.ChatUUID,
			Payload: map[string]interface{}{
				"user_uuid":  c.UserUUID,
				"email":      c.Email,
				"username":   c.Username,
				"device_id":  incoming.DeviceID,
				"emitted_at": time.Now().UTC().Format(time.RFC3339),
			},
		})

	case "chat_message":
		if incoming.ChatUUID == "" {
			c.sendError("chat_uuid is required")
			return
		}
		allowedRate, retryAfter, err := c.Hub.AllowMessage(context.Background(), c.UserUUID)
		if err != nil {
			log.Printf("message rate limit check failed: %v", err)
			c.sendError("message rate limit check failed")
			return
		}
		if !allowedRate {
			c.sendJSON(OutgoingMessage{
				Type:     "rate_limited",
				ChatUUID: incoming.ChatUUID,
				Payload: map[string]interface{}{
					"scope":               "messages",
					"retry_after_seconds": retryAfter,
				},
			})
			return
		}
		if incoming.ClientUUID == "" {
			c.sendError("client_uuid is required")
			return
		}
		if !c.Hub.IsSubscribed(c, incoming.ChatUUID) {
			c.sendError("subscribe to chat first")
			return
		}

		messageType := incoming.MessageType
		if messageType == "" {
			messageType = "text"
		}

		text := strings.TrimSpace(incoming.Text)
		if messageType == "text" && text == "" {
			payload := incoming.Payload
			if payload == nil || payload["attachment_uuids"] == nil {
				c.sendError("text is required for text messages without attachments")
				return
			}
		}

		allowed, membership, err := c.Hub.CanSendInChat(context.Background(), incoming.ChatUUID, c.UserUUID)
		if err != nil {
			log.Printf("send chat access check failed: %v", err)
			c.sendError("send permission check failed")
			return
		}
		if !allowed {
			if membership != nil && !membership.CanSendMessages {
				c.sendError("you are not allowed to send messages in this chat")
				return
			}
			c.sendError("you are not a member of this chat")
			return
		}

		sentAt := time.Now().UTC().Format(time.RFC3339)

		streamID, err := c.Hub.PublishPendingChatMessage(context.Background(), eventstream.PendingChatMessage{
			Event:          "pending_save",
			ChatUUID:       incoming.ChatUUID,
			SenderUUID:     c.UserUUID,
			SenderEmail:    c.Email,
			SenderUsername: c.Username,
			MessageType:    messageType,
			ClientUUID:     incoming.ClientUUID,
			ReplyToUUID:    incoming.ReplyToUUID,
			Text:           text,
			Payload:        incoming.Payload,
			SentAt:         sentAt,
		})
		if err != nil {
			log.Printf("stream publish failed: %v", err)
			c.sendError("failed to queue message")
			return
		}

		c.sendJSON(OutgoingMessage{
			Type:     "message_accepted",
			ChatUUID: incoming.ChatUUID,
			Payload: map[string]interface{}{
				"client_uuid": incoming.ClientUUID,
				"stream_id":   streamID,
				"status":      "queued",
				"queued_at":   sentAt,
			},
		})

		c.Hub.BroadcastToChat(incoming.ChatUUID, OutgoingMessage{
			Type:     "chat_message",
			ChatUUID: incoming.ChatUUID,
			Payload: map[string]interface{}{
				"sender_uuid":     c.UserUUID,
				"sender_email":    c.Email,
				"sender_username": c.Username,
				"client_uuid":     incoming.ClientUUID,
				"message_type":    messageType,
				"reply_to_uuid":   incoming.ReplyToUUID,
				"text":            text,
				"payload":         incoming.Payload,
				"stream_id":       streamID,
				"status":          "queued",
				"sent_at":         sentAt,
			},
		})

	case "message_delivered", "message_read":
		if incoming.ChatUUID == "" {
			c.sendError("chat_uuid is required")
			return
		}
		if incoming.MessageUUID == "" {
			c.sendError("message_uuid is required")
			return
		}
		allowedRate, retryAfter, err := c.Hub.AllowStatus(context.Background(), c.UserUUID)
		if err != nil {
			log.Printf("status rate limit check failed: %v", err)
			c.sendError("status rate limit check failed")
			return
		}
		if !allowedRate {
			c.sendJSON(OutgoingMessage{
				Type:     "rate_limited",
				ChatUUID: incoming.ChatUUID,
				Payload: map[string]interface{}{
					"scope":               "statuses",
					"retry_after_seconds": retryAfter,
				},
			})
			return
		}

		allowed, _, err := c.Hub.CanAccessChat(context.Background(), incoming.ChatUUID, c.UserUUID)
		if err != nil {
			log.Printf("status chat access check failed: %v", err)
			c.sendError("status permission check failed")
			return
		}
		if !allowed {
			c.sendError("you are not a member of this chat")
			return
		}

		statusEvent := "delivered"
		acceptedType := "delivery_accepted"
		if incoming.Type == "message_read" {
			statusEvent = "read"
			acceptedType = "read_accepted"
		}

		streamID, err := c.Hub.PublishMessageStatusEvent(context.Background(), eventstream.MessageStatusEvent{
			Event:       statusEvent,
			ChatUUID:    incoming.ChatUUID,
			MessageUUID: incoming.MessageUUID,
			UserUUID:    c.UserUUID,
			DeviceID:    incoming.DeviceID,
			SentAt:      time.Now().UTC().Format(time.RFC3339),
		})
		if err != nil {
			log.Printf("status stream publish failed: %v", err)
			c.sendError("failed to queue status event")
			return
		}

		c.sendJSON(OutgoingMessage{
			Type:     acceptedType,
			ChatUUID: incoming.ChatUUID,
			Payload: map[string]interface{}{
				"message_uuid": incoming.MessageUUID,
				"stream_id":    streamID,
				"status":       "queued",
			},
		})

	case "join_call":
		if incoming.ChatUUID == "" || incoming.CallUUID == "" || incoming.RoomKey == "" {
			c.sendError("chat_uuid, call_uuid and room_key are required")
			return
		}

		allowed, _, err := c.Hub.CanAccessChat(context.Background(), incoming.ChatUUID, c.UserUUID)
		if err != nil {
			log.Printf("join call access check failed: %v", err)
			c.sendError("call access check failed")
			return
		}
		if !allowed {
			c.sendError("you are not a member of this chat")
			return
		}

		existingPeers := c.Hub.JoinCallRoom(c, incoming.RoomKey)

		c.sendJSON(OutgoingMessage{
			Type:     "joined_call",
			ChatUUID: incoming.ChatUUID,
			CallUUID: incoming.CallUUID,
			RoomKey:  incoming.RoomKey,
			PeerID:   c.PeerID,
			Payload: map[string]interface{}{
				"peer_id":        c.PeerID,
				"existing_peers": existingPeers,
			},
		})

		c.Hub.BroadcastToCallRoom(incoming.RoomKey, c, OutgoingMessage{
			Type:     "call_new_peer",
			ChatUUID: incoming.ChatUUID,
			CallUUID: incoming.CallUUID,
			RoomKey:  incoming.RoomKey,
			PeerID:   c.PeerID,
			Payload: map[string]interface{}{
				"peer_id": c.PeerID,
			},
		})

	case "leave_call":
		if incoming.RoomKey == "" {
			c.sendError("room_key is required")
			return
		}

		c.Hub.LeaveCallRoom(c, incoming.RoomKey)

		c.Hub.BroadcastToCallRoom(incoming.RoomKey, c, OutgoingMessage{
			Type:     "call_peer_left",
			ChatUUID: incoming.ChatUUID,
			CallUUID: incoming.CallUUID,
			RoomKey:  incoming.RoomKey,
			PeerID:   c.PeerID,
			Payload: map[string]interface{}{
				"peer_id": c.PeerID,
			},
		})

	case "call_offer", "call_answer":
		if incoming.ChatUUID == "" || incoming.CallUUID == "" || incoming.RoomKey == "" || incoming.SDP == "" {
			c.sendError("chat_uuid, call_uuid, room_key and sdp are required")
			return
		}
		if !c.Hub.IsInCallRoom(c, incoming.RoomKey) {
			c.sendError("join call room first")
			return
		}

		c.Hub.BroadcastToCallRoom(incoming.RoomKey, c, OutgoingMessage{
			Type:     incoming.Type,
			ChatUUID: incoming.ChatUUID,
			CallUUID: incoming.CallUUID,
			RoomKey:  incoming.RoomKey,
			PeerID:   c.PeerID,
			SDP:      incoming.SDP,
			SDPType:  incoming.SDPType,
			Payload: map[string]interface{}{
				"peer_id": c.PeerID,
			},
		})

	case "call_ice":
		if incoming.ChatUUID == "" || incoming.CallUUID == "" || incoming.RoomKey == "" || incoming.Candidate == nil {
			c.sendError("chat_uuid, call_uuid, room_key and candidate are required")
			return
		}
		if !c.Hub.IsInCallRoom(c, incoming.RoomKey) {
			c.sendError("join call room first")
			return
		}

		c.Hub.BroadcastToCallRoom(incoming.RoomKey, c, OutgoingMessage{
			Type:      "call_ice",
			ChatUUID:  incoming.ChatUUID,
			CallUUID:  incoming.CallUUID,
			RoomKey:   incoming.RoomKey,
			PeerID:    c.PeerID,
			Candidate: incoming.Candidate,
			Payload: map[string]interface{}{
				"peer_id": c.PeerID,
			},
		})

	default:
		c.sendError("unsupported message type")
	}
}

func (c *Client) sendError(detail string) {
	c.sendJSON(OutgoingMessage{
		Type: "error",
		Payload: map[string]interface{}{
			"detail": detail,
		},
	})
}

func (c *Client) sendJSON(message OutgoingMessage) {
	payload, err := json.Marshal(message)
	if err != nil {
		log.Printf("sendJSON marshal failed: %v", err)
		return
	}

	select {
	case c.Send <- payload:
	default:
		c.Hub.Unregister(c)
	}
}