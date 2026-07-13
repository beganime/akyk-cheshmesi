#!/bin/sh
set -eu

: "${CALL_TURN_SECRET:?CALL_TURN_SECRET is required}"
: "${CALL_TURN_EXTERNAL_IP:?CALL_TURN_EXTERNAL_IP is required}"

exec turnserver \
  --listening-port=3478 \
  --min-port=49160 \
  --max-port=49200 \
  --external-ip="${CALL_TURN_EXTERNAL_IP}" \
  --realm="${CALL_TURN_REALM:-akyl-cheshmesi.ru}" \
  --use-auth-secret \
  --static-auth-secret="${CALL_TURN_SECRET}" \
  --fingerprint \
  --no-cli \
  --no-multicast-peers \
  --no-loopback-peers \
  --stale-nonce=600 \
  --log-file=stdout
