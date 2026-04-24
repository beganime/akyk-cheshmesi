package calls

import (
	"encoding/json"
	"log"
	"sync"

	"github.com/google/uuid"
	"github.com/pion/webrtc/v3"
)

type RemoteSenderBinding struct {
	Sender          *webrtc.RTPSender
	PublisherPeerID string
	TrackID         string
}

type Peer struct {
	ID       string
	UserUUID string
	Email    string
	Username string

	ws   *SafeWS
	pc   *webrtc.PeerConnection
	room *Room

	writeMu sync.Mutex
	stateMu sync.RWMutex

	localTracks   map[string]*webrtc.TrackLocalStaticRTP
	remoteSenders map[string]*RemoteSenderBinding

	done chan struct{}
}

func NewPeer(
	ws *SafeWS,
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
		ID:            id,
		UserUUID:      userUUID,
		Email:         email,
		Username:      username,
		ws:            ws,
		pc:            pc,
		room:          room,
		localTracks:   make(map[string]*webrtc.TrackLocalStaticRTP),
		remoteSenders: make(map[string]*RemoteSenderBinding),
		done:          make(chan struct{}),
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
		baseTrackID := remoteTrack.ID()
		if baseTrackID == "" {
			baseTrackID = uuid.New().String()
		}
		trackID := p.ID + ":" + baseTrackID + ":" + remoteTrack.Kind().String()

		log.Printf(
			"[calls][peer=%s] got track kind=%s codec=%s track_id=%s",
			p.ID[:8],
			remoteTrack.Kind().String(),
			remoteTrack.Codec().MimeType,
			trackID,
		)

		localTrack, err := webrtc.NewTrackLocalStaticRTP(
			remoteTrack.Codec().RTPCodecCapability,
			trackID,
			"stream-"+p.ID[:8],
		)
		if err != nil {
			log.Printf("[calls][peer=%s] create local track failed: %v", p.ID[:8], err)
			return
		}

		p.stateMu.Lock()
		p.localTracks[trackID] = localTrack
		p.stateMu.Unlock()

		p.room.RegisterPublishedTrack(p, trackID, localTrack)

		go func() {
			buf := make([]byte, 1500)
			for {
				n, _, readErr := remoteTrack.Read(buf)
				if readErr != nil {
					log.Printf("[calls][peer=%s] track read failed: %v", p.ID[:8], readErr)
					p.removeLocalTrack(trackID)
					p.room.UnpublishTrack(p.ID, trackID)
					return
				}

				if _, writeErr := localTrack.Write(buf[:n]); writeErr != nil {
					log.Printf("[calls][peer=%s] track write failed: %v", p.ID[:8], writeErr)
					p.removeLocalTrack(trackID)
					p.room.UnpublishTrack(p.ID, trackID)
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

	if err := p.ws.WriteSignal(sig); err != nil {
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

func (p *Peer) AddTrack(track *webrtc.TrackLocalStaticRTP, publisherPeerID string, trackID string) error {
	if publisherPeerID == p.ID {
		return nil
	}

	p.stateMu.RLock()
	if _, exists := p.remoteSenders[trackID]; exists {
		p.stateMu.RUnlock()
		return nil
	}
	p.stateMu.RUnlock()

	sender, err := p.pc.AddTrack(track)
	if err != nil {
		return err
	}

	p.stateMu.Lock()
	p.remoteSenders[trackID] = &RemoteSenderBinding{
		Sender:          sender,
		PublisherPeerID: publisherPeerID,
		TrackID:         trackID,
	}
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

func (p *Peer) RemovePublisherTracks(publisherPeerID string) error {
	p.stateMu.Lock()
	toRemove := make([]*webrtc.RTPSender, 0)
	removed := false

	for trackID, binding := range p.remoteSenders {
		if binding.PublisherPeerID == publisherPeerID {
			toRemove = append(toRemove, binding.Sender)
			delete(p.remoteSenders, trackID)
			removed = true
		}
	}
	p.stateMu.Unlock()

	if !removed {
		return nil
	}

	for _, sender := range toRemove {
		if err := p.pc.RemoveTrack(sender); err != nil {
			log.Printf("[calls][peer=%s] remove track failed: %v", p.ID[:8], err)
		}
	}

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

func (p *Peer) SnapshotLocalTracks() map[string]*webrtc.TrackLocalStaticRTP {
	p.stateMu.RLock()
	defer p.stateMu.RUnlock()

	out := make(map[string]*webrtc.TrackLocalStaticRTP, len(p.localTracks))
	for key, track := range p.localTracks {
		out[key] = track
	}
	return out
}

func (p *Peer) removeLocalTrack(trackID string) {
	p.stateMu.Lock()
	defer p.stateMu.Unlock()
	delete(p.localTracks, trackID)
}

func (p *Peer) Close() {
	select {
	case <-p.done:
		return
	default:
		close(p.done)
	}

	if p.room != nil {
		p.room.RemovePeer(p.ID)
	}
	if p.pc != nil {
		_ = p.pc.Close()
	}
	if p.ws != nil {
		_ = p.ws.Close()
	}
}