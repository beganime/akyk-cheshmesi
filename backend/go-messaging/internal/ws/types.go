package ws

type IceCandidate struct {
	Candidate        string `json:"candidate"`
	SDPMid          string `json:"sdpMid,omitempty"`
	SDPMLineIndex   *int   `json:"sdpMLineIndex,omitempty"`
	UsernameFragment string `json:"usernameFragment,omitempty"`
}

type IncomingMessage struct {
	Type        string                 `json:"type"`
	ChatUUID    string                 `json:"chat_uuid,omitempty"`
	ClientUUID  string                 `json:"client_uuid,omitempty"`
	MessageUUID string                 `json:"message_uuid,omitempty"`
	MessageType string                 `json:"message_type,omitempty"`
	ReplyToUUID string                 `json:"reply_to_uuid,omitempty"`
	DeviceID    string                 `json:"device_id,omitempty"`
	Text        string                 `json:"text,omitempty"`
	Payload     map[string]interface{} `json:"payload,omitempty"`

	CallUUID  string        `json:"call_uuid,omitempty"`
	RoomKey   string        `json:"room_key,omitempty"`
	PeerID    string        `json:"peer_id,omitempty"`
	SDP       string        `json:"sdp,omitempty"`
	SDPType   string        `json:"sdp_type,omitempty"`
	Candidate *IceCandidate `json:"candidate,omitempty"`
}

type OutgoingMessage struct {
	Type     string      `json:"type"`
	ChatUUID string      `json:"chat_uuid,omitempty"`
	Payload  interface{} `json:"payload,omitempty"`

	CallUUID  string        `json:"call_uuid,omitempty"`
	RoomKey   string        `json:"room_key,omitempty"`
	PeerID    string        `json:"peer_id,omitempty"`
	SDP       string        `json:"sdp,omitempty"`
	SDPType   string        `json:"sdp_type,omitempty"`
	Candidate *IceCandidate `json:"candidate,omitempty"`
}