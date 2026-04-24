package calls

import (
	"context"
	"encoding/json"
	"log"
	"strings"
	"time"

	"akyl-chesmesi/go-messaging/internal/chataccess"

	"github.com/gorilla/websocket"
)

const (
	callPongWait   = 60 * time.Second
	callPingPeriod = 20 * time.Second
)

type SignalingHandler struct {
	conn          *websocket.Conn
	ws            *SafeWS
	roomManager   *RoomManager
	accessService *chataccess.Service

	userUUID string
	email    string
	username string

	peer *Peer
	room *Room
}

func NewSignalingHandler(
	conn *websocket.Conn,
	roomManager *RoomManager,
	accessService *chataccess.Service,
	userUUID string,
	email string,
	username string,
) *SignalingHandler {
	return &SignalingHandler{
		conn:          conn,
		ws:            NewSafeWS(conn),
		roomManager:   roomManager,
		accessService: accessService,
		userUUID:      userUUID,
		email:         email,
		username:      username,
	}
}

func (h *SignalingHandler) Handle(readLimit int64) {
	if readLimit <= 0 {
		readLimit = 65536
	}

	h.conn.SetReadLimit(readLimit)
	_ = h.conn.SetReadDeadline(time.Now().Add(callPongWait))
	h.conn.SetPongHandler(func(string) error {
		return h.conn.SetReadDeadline(time.Now().Add(callPongWait))
	})

	pingTicker := time.NewTicker(callPingPeriod)
	defer pingTicker.Stop()

	done := make(chan struct{})
	go func() {
		defer close(done)
		for range pingTicker.C {
			if err := h.ws.WritePing(); err != nil {
				return
			}
		}
	}()

	defer func() {
		if h.peer != nil {
			h.peer.Close()
		}
		if h.room != nil {
			h.roomManager.Cleanup(h.room.ID)
		}
		_ = h.ws.Close()
		log.Printf("[calls] signaling connection closed for user=%s", h.userUUID)
	}()

	for {
		_, rawMsg, err := h.conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(
				err,
				websocket.CloseGoingAway,
				websocket.CloseAbnormalClosure,
			) {
				log.Printf("[calls] read error user=%s: %v", h.userUUID, err)
			}
			return
		}

		_ = h.conn.SetReadDeadline(time.Now().Add(callPongWait))

		var sig Signal
		if err := json.Unmarshal(rawMsg, &sig); err != nil {
			h.sendError("invalid JSON payload")
			continue
		}

		switch strings.TrimSpace(sig.Type) {
		case "ping":
			h.send(Signal{
				Type: "pong",
				Payload: map[string]interface{}{
					"user_uuid": h.userUUID,
				},
			})

		case "join_call":
			if h.peer != nil {
				h.sendError("already joined to a call room")
				continue
			}
			if sig.ChatUUID == "" {
				h.sendError("chat_uuid is required")
				continue
			}
			if sig.RoomKey == "" {
				h.sendError("room_key is required")
				continue
			}

			allowed, _, err := h.accessService.CanAccessChat(context.Background(), sig.ChatUUID, h.userUUID)
			if err != nil {
				log.Printf("[calls] access check failed user=%s chat=%s: %v", h.userUUID, sig.ChatUUID, err)
				h.sendError("chat access check failed")
				continue
			}
			if !allowed {
				h.sendError("you are not a member of this chat")
				continue
			}

			room := h.roomManager.GetOrCreate(sig.ChatUUID, sig.RoomKey)
			peer, err := NewPeer(
				h.ws,
				room,
				h.userUUID,
				h.email,
				h.username,
				h.roomManager.ICEServers(),
			)
			if err != nil {
				log.Printf("[calls] peer create failed user=%s: %v", h.userUUID, err)
				h.sendError("failed to create call peer")
				continue
			}

			if err := room.AddPeer(peer); err != nil {
				log.Printf("[calls] room add peer failed user=%s: %v", h.userUUID, err)
				h.sendError(err.Error())
				continue
			}

			h.room = room
			h.peer = peer

			peer.Send(Signal{
				Type:     "joined_call",
				ChatUUID: sig.ChatUUID,
				CallUUID: sig.CallUUID,
				RoomKey:  sig.RoomKey,
				PeerID:   peer.ID,
				Payload: map[string]interface{}{
					"user_uuid":         h.userUUID,
					"email":             h.email,
					"username":          h.username,
					"participant_count": room.Count(),
				},
			})

		case "call_offer":
			if h.peer == nil {
				h.sendError("join_call required before call_offer")
				continue
			}
			if sig.SDP == "" {
				h.sendError("sdp is required")
				continue
			}
			if err := h.peer.HandleOffer(sig.SDP); err != nil {
				log.Printf("[calls] handle offer failed peer=%s: %v", h.peer.ID, err)
				h.sendError("offer handling failed")
			}

		case "call_answer":
			if h.peer == nil {
				h.sendError("join_call required before call_answer")
				continue
			}
			if sig.SDP == "" {
				h.sendError("sdp is required")
				continue
			}
			if err := h.peer.HandleAnswer(sig.SDP); err != nil {
				log.Printf("[calls] handle answer failed peer=%s: %v", h.peer.ID, err)
				h.sendError("answer handling failed")
			}

		case "call_ice":
			if h.peer == nil {
				h.sendError("join_call required before call_ice")
				continue
			}
			if len(sig.Candidate) == 0 {
				h.sendError("candidate is required")
				continue
			}
			if err := h.peer.HandleICECandidate(sig.Candidate); err != nil {
				log.Printf("[calls] handle ICE failed peer=%s: %v", h.peer.ID, err)
				h.sendError("ICE candidate handling failed")
			}

		case "leave_call":
			return

		default:
			h.sendError("unsupported signaling type")
		}
	}
}

func (h *SignalingHandler) send(sig Signal) {
	if err := h.ws.WriteSignal(sig); err != nil {
		log.Printf("[calls] write send failed: %v", err)
	}
}

func (h *SignalingHandler) sendError(detail string) {
	h.send(Signal{
		Type: "error",
		Payload: map[string]interface{}{
			"detail": detail,
		},
	})
}