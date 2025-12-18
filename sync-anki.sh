#!/bin/bash
# AnkAi - Trigger Anki sync with AnkiWeb
# Add to crontab for periodic syncing:
#   0 * * * * /path/to/AnkAi/sync-anki.sh

ANKI_CONNECT_URL="${ANKI_CONNECT_URL:-http://localhost:8765}"

response=$(curl -s "$ANKI_CONNECT_URL" -X POST \
  -H "Content-Type: application/json" \
  -d '{"action": "sync", "version": 6}')

if echo "$response" | grep -q '"error": null'; then
  echo "$(date): Anki sync completed successfully"
else
  echo "$(date): Anki sync failed - $response" >&2
  exit 1
fi
