package calls

import (
	"encoding/json"
	"log"
	"sync"

	"github.com/google/uuid"
	"github.com/gorilla/websocket"
	"github.com/pion/webrtc/v3"
)

type Peer struct {
	ID       string
	UserUUID string
	Email    string
	Username string

	conn *websocket.Conn
	pc   *webrtc.PeerConnection
	room *Room

	writeMu sync.Mutex
	stateMu sync.RWMutex

	localTracks   []*webrtc.TrackLocalStaticRTP
	remoteSenders []*webrtc.RTPSender

	done chan struct{}
}

func NewPeer(
	conn *websocket.Conn,
	room *Room,
	userUUID string,
	email string,
	username string,
	iceServers []webrtc.ICEServer,
) (*Peer, error) {
	id := uuid.New().String()

	pc, err := webrtc.NewPeerConnection(webrtc.Configuration{
		ICEServers: iceServers,
	})
	if err != nil {
		return nil, err
	}

	p := &Peer{
		ID:       id,
		UserUUID: userUUID,
		Email:    email,
		Username: username,
		conn:     conn,
		pc:       pc,
		room:     room,
		done:     make(chan struct{}),
	}

	pc.OnICECandidate(func(c *webrtc.ICECandidate) {
		if c == nil {
			return
		}

		candidateJSON, err := json.Marshal(c.ToJSON())
		if err != nil {
			log.Printf("[calls][peer=%s] ice marshal failed: %v", p.ID[:8], err)
			return
		}

		p.Send(Signal{
			Type:      "call_ice",
			ChatUUID:  p.room.ChatUUID,
			RoomKey:   p.room.ID,
			PeerID:    p.ID,
			Candidate: candidateJSON,
		})
	})

	pc.OnICEConnectionStateChange(func(state webrtc.ICEConnectionState) {
		log.Printf("[calls][peer=%s] ICE state=%s", p.ID[:8], state.String())

		if state == webrtc.ICEConnectionStateFailed || state == webrtc.ICEConnectionStateClosed {
			p.Close()
		}
	})

	pc.OnTrack(func(remoteTrack *webrtc.TrackRemote, receiver *webrtc.RTPReceiver) {
		log.Printf(
			"[calls][peer=%s] got track kind=%s codec=%s",
			p.ID[:8],
			remoteTrack.Kind().String(),
			remoteTrack.Codec().MimeType,
		)

		localTrack, err := webrtc.NewTrackLocalStaticRTP(
			remoteTrack.Codec().RTPCodecCapability,
			remoteTrack.Kind().String()+"-"+p.ID[:8],
			"stream-"+p.ID[:8],
		)
		if err != nil {
			log.Printf("[calls][peer=%s] create local track failed: %v", p.ID[:8], err)
			return
		}

		p.stateMu.Lock()
		p.localTracks = append(p.localTracks, localTrack)
		p.stateMu.Unlock()

		p.room.BroadcastTrack(p, localTrack)

		go func() {
			buf := make([]byte, 1500)
			for {
				n, _, readErr := remoteTrack.Read(buf)
				if readErr != nil {
					log.Printf("[calls][peer=%s] track read failed: %v", p.ID[:8], readErr)
					return
				}

				if _, writeErr := localTrack.Write(buf[:n]); writeErr != nil {
					log.Printf("[calls][peer=%s] track write failed: %v", p.ID[:8], writeErr)
					return
				}
			}
		}()
	})

	return p, nil
}

func (p *Peer) Send(sig Signal) {
	p.writeMu.Lock()
	defer p.writeMu.Unlock()

	payload, err := json.Marshal(sig)
	if err != nil {
		log.Printf("[calls][peer=%s] send marshal failed: %v", p.ID[:8], err)
		return
	}

	if err := p.conn.WriteMessage(websocket.TextMessage, payload); err != nil {
		log.Printf("[calls][peer=%s] send failed: %v", p.ID[:8], err)
	}
}

func (p *Peer) HandleOffer(sdp string) error {
	if err := p.pc.SetRemoteDescription(webrtc.SessionDescription{
		Type: webrtc.SDPTypeOffer,
		SDP:  sdp,
	}); err != nil {
		return err
	}

	answer, err := p.pc.CreateAnswer(nil)
	if err != nil {
		return err
	}

	gatherComplete := webrtc.GatheringCompletePromise(p.pc)

	if err := p.pc.SetLocalDescription(answer); err != nil {
		return err
	}

	<-gatherComplete

	p.Send(Signal{
		Type:     "call_answer",
		ChatUUID: p.room.ChatUUID,
		RoomKey:  p.room.ID,
		PeerID:   p.ID,
		SDP:      p.pc.LocalDescription().SDP,
		SDPType:  "answer",
	})

	return nil
}

func (p *Peer) HandleAnswer(sdp string) error {
	return p.pc.SetRemoteDescription(webrtc.SessionDescription{
		Type: webrtc.SDPTypeAnswer,
		SDP:  sdp,
	})
}

func (p *Peer) HandleICECandidate(candidateJSON json.RawMessage) error {
	var candidate webrtc.ICECandidateInit
	if err := json.Unmarshal(candidateJSON, &candidate); err != nil {
		return err
	}
	return p.pc.AddICECandidate(candidate)
}

func (p *Peer) AddTrack(track *webrtc.TrackLocalStaticRTP) error {
	sender, err := p.pc.AddTrack(track)
	if err != nil {
		return err
	}

	p.stateMu.Lock()
	p.remoteSenders = append(p.remoteSenders, sender)
	p.stateMu.Unlock()

	go func() {
		buf := make([]byte, 1500)
		for {
			if _, _, err := sender.Read(buf); err != nil {
				return
			}
		}
	}()

	return p.Renegotiate()
}

func (p *Peer) Renegotiate() error {
	offer, err := p.pc.CreateOffer(nil)
	if err != nil {
		return err
	}

	gatherComplete := webrtc.GatheringCompletePromise(p.pc)

	if err := p.pc.SetLocalDescription(offer); err != nil {
		return err
	}

	<-gatherComplete

	p.Send(Signal{
		Type:     "call_offer",
		ChatUUID: p.room.ChatUUID,
		RoomKey:  p.room.ID,
		PeerID:   p.ID,
		SDP:      p.pc.LocalDescription().SDP,
		SDPType:  "offer",
	})

	return nil
}

func (p *Peer) GetLocalTracks() []*webrtc.TrackLocalStaticRTP {
	p.stateMu.RLock()
	defer p.stateMu.RUnlock()

	out := make([]*webrtc.TrackLocalStaticRTP, len(p.localTracks))
	copy(out, p.localTracks)
	return out
}

func (p *Peer) Close() {
	select {
	case <-p.done:
		return
	default:
		close(p.done)
	}

	if p.pc != nil {
		_ = p.pc.Close()
	}
	if p.conn != nil {
		_ = p.conn.Close()
	}
	if p.room != nil {
		p.room.RemovePeer(p.ID)
	}
}