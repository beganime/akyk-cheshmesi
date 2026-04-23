package calls

import (
	"log"
	"sync"

	"github.com/pion/webrtc/v3"
)

type Room struct {
	ID       string
	ChatUUID string

	peers map[string]*Peer
	mu    sync.RWMutex
}

func NewRoom(chatUUID string, roomKey string) *Room {
	return &Room{
		ID:       roomKey,
		ChatUUID: chatUUID,
		peers:    make(map[string]*Peer),
	}
}

func (r *Room) AddPeer(p *Peer) {
	r.mu.Lock()

	type existingPeerData struct {
		peer   *Peer
		tracks []*webrtc.TrackLocalStaticRTP
	}

	existing := make([]existingPeerData, 0, len(r.peers))
	for _, ep := range r.peers {
		tracks := ep.GetLocalTracks()
		existing = append(existing, existingPeerData{
			peer:   ep,
			tracks: tracks,
		})
	}

	r.peers[p.ID] = p
	r.mu.Unlock()

	log.Printf("[calls][room=%s] peer %s joined, total=%d", r.ID, p.ID[:8], r.Count())

	for _, item := range existing {
		item.peer.Send(Signal{
			Type:     "call_new_peer",
			ChatUUID: r.ChatUUID,
			RoomKey:  r.ID,
			PeerID:   p.ID,
			Payload: map[string]interface{}{
				"user_uuid": p.UserUUID,
				"email":     p.Email,
				"username":  p.Username,
			},
		})

		p.Send(Signal{
			Type:     "call_existing_peer",
			ChatUUID: r.ChatUUID,
			RoomKey:  r.ID,
			PeerID:   item.peer.ID,
			Payload: map[string]interface{}{
				"user_uuid": item.peer.UserUUID,
				"email":     item.peer.Email,
				"username":  item.peer.Username,
			},
		})
	}

	for _, item := range existing {
		for _, track := range item.tracks {
			if err := p.AddTrack(track); err != nil {
				log.Printf("[calls][room=%s] add existing track to %s failed: %v", r.ID, p.ID[:8], err)
			}
		}
	}
}

func (r *Room) RemovePeer(peerID string) {
	r.mu.Lock()
	delete(r.peers, peerID)
	r.mu.Unlock()

	log.Printf("[calls][room=%s] peer %s left, total=%d", r.ID, peerID[:8], r.Count())

	r.mu.RLock()
	peers := make([]*Peer, 0, len(r.peers))
	for _, ep := range r.peers {
		peers = append(peers, ep)
	}
	r.mu.RUnlock()

	for _, ep := range peers {
		ep.Send(Signal{
			Type:     "call_peer_left",
			ChatUUID: r.ChatUUID,
			RoomKey:  r.ID,
			PeerID:   peerID,
		})
	}
}

func (r *Room) BroadcastTrack(publisher *Peer, track *webrtc.TrackLocalStaticRTP) {
	r.mu.RLock()
	peers := make([]*Peer, 0, len(r.peers))
	for _, ep := range r.peers {
		if ep.ID == publisher.ID {
			continue
		}
		peers = append(peers, ep)
	}
	r.mu.RUnlock()

	for _, ep := range peers {
		if err := ep.AddTrack(track); err != nil {
			log.Printf("[calls][room=%s] broadcast track %s -> %s failed: %v", r.ID, publisher.ID[:8], ep.ID[:8], err)
		}
	}
}

func (r *Room) Count() int {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return len(r.peers)
}

type RoomManager struct {
	rooms      map[string]*Room
	iceServers []webrtc.ICEServer
	mu         sync.RWMutex
}

func NewRoomManager(iceServers []webrtc.ICEServer) *RoomManager {
	if len(iceServers) == 0 {
		iceServers = BuildICEServers(
			[]string{"stun:stun.l.google.com:19302", "stun:stun1.l.google.com:19302"},
			nil,
			"",
			"",
		)
	}

	return &RoomManager{
		rooms:      make(map[string]*Room),
		iceServers: iceServers,
	}
}

func (rm *RoomManager) GetOrCreate(chatUUID string, roomKey string) *Room {
	rm.mu.Lock()
	defer rm.mu.Unlock()

	if room, ok := rm.rooms[roomKey]; ok {
		return room
	}

	room := NewRoom(chatUUID, roomKey)
	rm.rooms[roomKey] = room
	log.Printf("[calls] created room=%s chat=%s", roomKey, chatUUID)
	return room
}

func (rm *RoomManager) Cleanup(roomKey string) {
	rm.mu.Lock()
	defer rm.mu.Unlock()

	room, ok := rm.rooms[roomKey]
	if !ok {
		return
	}
	if room.Count() > 0 {
		return
	}

	delete(rm.rooms, roomKey)
	log.Printf("[calls] removed empty room=%s", roomKey)
}

func (rm *RoomManager) ICEServers() []webrtc.ICEServer {
	rm.mu.RLock()
	defer rm.mu.RUnlock()

	out := make([]webrtc.ICEServer, len(rm.iceServers))
	copy(out, rm.iceServers)
	return out
}

func BuildICEServers(
	stunURLs []string,
	turnURLs []string,
	turnUsername string,
	turnCredential string,
) []webrtc.ICEServer {
	servers := make([]webrtc.ICEServer, 0, 2)

	if len(stunURLs) > 0 {
		servers = append(servers, webrtc.ICEServer{
			URLs: stunURLs,
		})
	}

	if len(turnURLs) > 0 {
		servers = append(servers, webrtc.ICEServer{
			URLs:       turnURLs,
			Username:   turnUsername,
			Credential: turnCredential,
		})
	}

	return servers
}