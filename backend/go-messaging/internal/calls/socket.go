package calls

import (
	"encoding/json"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

type SafeWS struct {
	conn *websocket.Conn
	mu   sync.Mutex
}

func NewSafeWS(conn *websocket.Conn) *SafeWS {
	return &SafeWS{conn: conn}
}

func (s *SafeWS) WriteSignal(sig Signal) error {
	payload, err := json.Marshal(sig)
	if err != nil {
		return err
	}
	return s.WriteMessage(websocket.TextMessage, payload)
}

func (s *SafeWS) WriteMessage(messageType int, payload []byte) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.conn.WriteMessage(messageType, payload)
}

func (s *SafeWS) WritePing() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.conn.WriteControl(
		websocket.PingMessage,
		[]byte("ping"),
		time.Now().Add(5*time.Second),
	)
}

func (s *SafeWS) Close() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.conn.Close()
}