package calls

import "encoding/json"

type Signal struct {
	Type      string                 `json:"type"`
	ChatUUID  string                 `json:"chat_uuid,omitempty"`
	CallUUID  string                 `json:"call_uuid,omitempty"`
	RoomKey   string                 `json:"room_key,omitempty"`
	PeerID    string                 `json:"peer_id,omitempty"`
	SDP       string                 `json:"sdp,omitempty"`
	SDPType   string                 `json:"sdp_type,omitempty"`
	Candidate json.RawMessage        `json:"candidate,omitempty"`
	Payload   map[string]interface{} `json:"payload,omitempty"`
}