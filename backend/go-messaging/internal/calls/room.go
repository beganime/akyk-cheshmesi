package calls

import (
	"context"
	"errors"
	"log"
	"sort"
	"sync"
	"time"

	"github.com/pion/webrtc/v3"
)

type publishedTrackInfo struct {
	PublisherPeerID string
	TrackID         string
	Track           *webrtc.TrackLocalStaticRTP
}

type Room struct {
	ID       string
	ChatUUID string

	maxPeers int

	peers          map[string]*Peer
	users          map[string]*Peer
	publishedTracks map[string]map[string]*webrtc.TrackLocalStaticRTP

	createdAt   time.Time
	lastEmptyAt time.Time

	mu sync.RWMutex
}

func NewRoom(chatUUID string, roomKey string, maxPeers int) *Room {
	if maxPeers <= 0 {
		maxPeers = 8
	}

	now := time.Now()
	return &Room{
		ID:              roomKey,
		ChatUUID:        chatUUID,
		maxPeers:        maxPeers,
		peers:           make(map[string]*Peer),
		users:           make(map[string]*Peer),
		publishedTracks: make(map[string]map[string]*webrtc.TrackLocalStaticRTP),
		createdAt:       now,
		lastEmptyAt:     now,
	}
}

func (r *Room) Touch() {
	r.mu.Lock()
	r.lastEmptyAt = time.Time{}
	r.mu.Unlock()
}

func (r *Room) AddPeer(p *Peer) error {
	r.mu.Lock()

	var replacedPeer *Peer
	if currentForUser, ok := r.users[p.UserUUID]; ok {
		replacedPeer = currentForUser
		delete(r.peers, currentForUser.ID)
	}

	if len(r.peers) >= r.maxPeers {
		r.mu.Unlock()
		return errors.New("room is full")
	}

	existingPeers := make([]*Peer, 0, len(r.peers))
	for _, ep := range r.peers {
		existingPeers = append(existingPeers, ep)
	}

	existingTracks := make([]publishedTrackInfo, 0)
	for publisherPeerID, tracksMap := range r.publishedTracks {
		for trackID, track := range tracksMap {
			existingTracks = append(existingTracks, publishedTrackInfo{
				PublisherPeerID: publisherPeerID,
				TrackID:         trackID,
				Track:           track,
			})
		}
	}

	r.peers[p.ID] = p
	r.users[p.UserUUID] = p
	r.lastEmptyAt = time.Time{}

	r.mu.Unlock()

	if replacedPeer != nil {
		log.Printf("[calls][room=%s] replacing previous peer for user=%s", r.ID, p.UserUUID)
		go replacedPeer.Close()
	}

	log.Printf("[calls][room=%s] peer %s joined, total=%d", r.ID, p.ID[:8], r.Count())

	for _, ep := range existingPeers {
		ep.Send(Signal{
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
			PeerID:   ep.ID,
			Payload: map[string]interface{}{
				"user_uuid": ep.UserUUID,
				"email":     ep.Email,
				"username":  ep.Username,
			},
		})
	}

	for _, item := range existingTracks {
		if err := p.AddTrack(item.Track, item.PublisherPeerID, item.TrackID); err != nil {
			log.Printf(
				"[calls][room=%s] add existing track to %s failed: %v",
				r.ID,
				p.ID[:8],
				err,
			)
		}
	}

	return nil
}

func (r *Room) RegisterPublishedTrack(publisher *Peer, trackID string, track *webrtc.TrackLocalStaticRTP) {
	r.mu.Lock()
	if _, ok := r.publishedTracks[publisher.ID]; !ok {
		r.publishedTracks[publisher.ID] = make(map[string]*webrtc.TrackLocalStaticRTP)
	}
	r.publishedTracks[publisher.ID][trackID] = track

	targets := make([]*Peer, 0, len(r.peers))
	for _, ep := range r.peers {
		if ep.ID == publisher.ID {
			continue
		}
		targets = append(targets, ep)
	}
	r.lastEmptyAt = time.Time{}
	r.mu.Unlock()

	for _, ep := range targets {
		if err := ep.AddTrack(track, publisher.ID, trackID); err != nil {
			log.Printf(
				"[calls][room=%s] broadcast track %s -> %s failed: %v",
				r.ID,
				publisher.ID[:8],
				ep.ID[:8],
				err,
			)
		}
	}
}

func (r *Room) UnpublishTrack(publisherPeerID string, trackID string) {
	r.mu.Lock()
	if tracksMap, ok := r.publishedTracks[publisherPeerID]; ok {
		delete(tracksMap, trackID)
		if len(tracksMap) == 0 {
			delete(r.publishedTracks, publisherPeerID)
		}
	}

	targets := make([]*Peer, 0, len(r.peers))
	for _, ep := range r.peers {
		if ep.ID == publisherPeerID {
			continue
		}
		targets = append(targets, ep)
	}
	r.mu.Unlock()

	for _, ep := range targets {
		if err := ep.RemovePublisherTracks(publisherPeerID); err != nil {
			log.Printf(
				"[calls][room=%s] remove publisher tracks %s -> %s failed: %v",
				r.ID,
				publisherPeerID[:8],
				ep.ID[:8],
				err,
			)
		}
	}
}

func (r *Room) UnpublishPeerTracks(publisherPeerID string) {
	r.mu.Lock()
	_, hadTracks := r.publishedTracks[publisherPeerID]
	delete(r.publishedTracks, publisherPeerID)

	targets := make([]*Peer, 0, len(r.peers))
	for _, ep := range r.peers {
		if ep.ID == publisherPeerID {
			continue
		}
		targets = append(targets, ep)
	}
	r.mu.Unlock()

	if !hadTracks {
		return
	}

	for _, ep := range targets {
		if err := ep.RemovePublisherTracks(publisherPeerID); err != nil {
			log.Printf(
				"[calls][room=%s] remove peer tracks %s -> %s failed: %v",
				r.ID,
				publisherPeerID[:8],
				ep.ID[:8],
				err,
			)
		}
	}
}

func (r *Room) RemovePeer(peerID string) {
	r.mu.Lock()

	var userUUID string
	if existingPeer, ok := r.peers[peerID]; ok {
		userUUID = existingPeer.UserUUID
	}

	delete(r.peers, peerID)

	if userUUID != "" {
		if current, ok := r.users[userUUID]; ok && current.ID == peerID {
			delete(r.users, userUUID)
		}
	}

	isEmptyNow := len(r.peers) == 0
	if isEmptyNow {
		r.lastEmptyAt = time.Now()
	}

	targets := make([]*Peer, 0, len(r.peers))
	for _, ep := range r.peers {
		targets = append(targets, ep)
	}

	r.mu.Unlock()

	r.UnpublishPeerTracks(peerID)

	log.Printf("[calls][room=%s] peer %s left, total=%d", r.ID, peerID[:8], r.Count())

	for _, ep := range targets {
		ep.Send(Signal{
			Type:     "call_peer_left",
			ChatUUID: r.ChatUUID,
			RoomKey:  r.ID,
			PeerID:   peerID,
		})
	}
}

func (r *Room) Count() int {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return len(r.peers)
}

func (r *Room) IsEmptyFor(ttl time.Duration) bool {
	r.mu.RLock()
	defer r.mu.RUnlock()

	if len(r.peers) > 0 {
		return false
	}
	if r.lastEmptyAt.IsZero() {
		return false
	}
	return time.Since(r.lastEmptyAt) >= ttl
}

type RoomManager struct {
	rooms        map[string]*Room
	iceServers   []webrtc.ICEServer
	maxPeers     int
	emptyRoomTTL time.Duration
	mu           sync.RWMutex
}

func NewRoomManager(
	iceServers []webrtc.ICEServer,
	maxPeers int,
	emptyRoomTTL time.Duration,
) *RoomManager {
	if len(iceServers) == 0 {
		iceServers = BuildICEServers(
			[]string{"stun:stun.l.google.com:19302", "stun:stun1.l.google.com:19302"},
			nil,
			"",
			"",
		)
	}
	if maxPeers <= 0 {
		maxPeers = 8
	}
	if emptyRoomTTL <= 0 {
		emptyRoomTTL = 30 * time.Second
	}

	return &RoomManager{
		rooms:        make(map[string]*Room),
		iceServers:   iceServers,
		maxPeers:     maxPeers,
		emptyRoomTTL: emptyRoomTTL,
	}
}

func (rm *RoomManager) GetOrCreate(chatUUID string, roomKey string) *Room {
	rm.mu.Lock()
	defer rm.mu.Unlock()

	if room, ok := rm.rooms[roomKey]; ok {
		return room
	}

	room := NewRoom(chatUUID, roomKey, rm.maxPeers)
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

func (rm *RoomManager) StartCleanupLoop(ctx context.Context, interval time.Duration) {
	if interval <= 0 {
		interval = 15 * time.Second
	}

	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			rm.cleanupExpiredEmptyRooms()
		}
	}
}

func (rm *RoomManager) cleanupExpiredEmptyRooms() {
	rm.mu.Lock()
	defer rm.mu.Unlock()

	for roomKey, room := range rm.rooms {
		if room.IsEmptyFor(rm.emptyRoomTTL) {
			delete(rm.rooms, roomKey)
			log.Printf("[calls] cleanup loop removed room=%s", roomKey)
		}
	}
}

func (rm *RoomManager) ICEServers() []webrtc.ICEServer {
	rm.mu.RLock()
	defer rm.mu.RUnlock()

	out := make([]webrtc.ICEServer, len(rm.iceServers))
	copy(out, rm.iceServers)
	return out
}

type RoomStat struct {
	RoomKey           string   `json:"room_key"`
	ChatUUID          string   `json:"chat_uuid"`
	PeersCount        int      `json:"peers_count"`
	MaxPeers          int      `json:"max_peers"`
	ConnectedUserUUIDs []string `json:"connected_user_uuids"`
	CreatedAt         string   `json:"created_at"`
}

type RoomManagerStats struct {
	RoomsCount int        `json:"rooms_count"`
	Rooms      []RoomStat `json:"rooms"`
}

func (rm *RoomManager) Stats() RoomManagerStats {
	rm.mu.RLock()
	rooms := make([]*Room, 0, len(rm.rooms))
	for _, room := range rm.rooms {
		rooms = append(rooms, room)
	}
	rm.mu.RUnlock()

	sort.Slice(rooms, func(i, j int) bool {
		return rooms[i].ID < rooms[j].ID
	})

	result := RoomManagerStats{
		RoomsCount: len(rooms),
		Rooms:      make([]RoomStat, 0, len(rooms)),
	}

	for _, room := range rooms {
		room.mu.RLock()
		users := make([]string, 0, len(room.users))
		for userUUID := range room.users {
			users = append(users, userUUID)
		}
		sort.Strings(users)

		stat := RoomStat{
			RoomKey:            room.ID,
			ChatUUID:           room.ChatUUID,
			PeersCount:         len(room.peers),
			MaxPeers:           room.maxPeers,
			ConnectedUserUUIDs: users,
			CreatedAt:          room.createdAt.UTC().Format(time.RFC3339),
		}
		room.mu.RUnlock()

		result.Rooms = append(result.Rooms, stat)
	}

	return result
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