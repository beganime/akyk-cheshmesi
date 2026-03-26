package ws

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
}

type OutgoingMessage struct {
	Type     string      `json:"type"`
	ChatUUID string      `json:"chat_uuid,omitempty"`
	Payload  interface{} `json:"payload,omitempty"`
}