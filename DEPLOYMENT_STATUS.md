# AnkAi Deployment Status

## Current Deployment (as of 2025-12-22)

### Live URL
- **App**: http://130.162.167.220 (HTTP only - DuckDNS SSL had issues)
- **VNC (Anki Desktop)**: http://130.162.167.220:3000
- **Domain**: ainki.duckdns.org (configured but HTTPS not working due to DuckDNS DNS issues)

### Server Details
- **Provider**: Oracle Cloud Free Tier
- **Region**: UK South (London)
- **Instance**: VM.Standard.A1.Flex (ARM - but running x86 via emulation)
- **OS**: Oracle Linux 9
- **Public IP**: 130.162.167.220
- **SSH**: `ssh opc@130.162.167.220`

### Docker Setup
All services run via docker-compose:
```bash
cd ~/AnkAi
docker compose -f docker-compose.prod.yml up -d
```

**Containers**:
| Container | Image | Ports | Notes |
|-----------|-------|-------|-------|
| ankai-anki | mlcivilengineer/anki-desktop-docker:main | 3000 (VNC), 8765 (AnkiConnect internal) | Anki Desktop with AnkiConnect |
| ankai-backend | ankai-backend (local build) | 8000 (internal) | FastAPI backend |
| ankai-frontend | ankai-frontend (local build) | 80 (internal) | React frontend via nginx |
| ankai-caddy | caddy:2-alpine | 80, 443 | Reverse proxy |

### Key Configuration Files

**docker-compose.prod.yml changes from repo**:
- Anki volume: `/home/opc/anki-data:/config` (not the named volume)
- AnkiConnect addon location: `~/AnkAi/anki/addons21/2055492159/`
- Backend depends_on uses simple list (not service_healthy condition)

**Caddyfile** (currently HTTP only):
```
:80 {
    handle /api/* {
        reverse_proxy backend:8000
    }
    handle {
        reverse_proxy frontend:80
    }
}
```

### AnkiConnect Setup
- Addon ID: 2055492159
- Config location: `~/AnkAi/anki/addons21/2055492159/config.json`
- Config content:
```json
{
    "apiKey": null,
    "apiLogPath": null,
    "ignoreOriginList": [],
    "webBindAddress": "0.0.0.0",
    "webBindPort": 8765,
    "webCorsOriginList": ["*"]
}
```

### Environment Variables
Located at `~/AnkAi/.env`:
```
LLM_PROVIDER=groq
GROQ_API_KEY=<user's key>
GROQ_MODEL=llama-3.3-70b-versatile
```

### Firewall Rules (Oracle Cloud Security List)
- Port 80 (HTTP)
- Port 443 (HTTPS)
- Port 3000 (VNC - for Anki setup)

Also configured via `firewall-cmd` on the VM itself.

---

## Common Operations

### Rebuild after code changes
```bash
# On local machine
git add -A && git commit -m "message" && git push

# On server (or via SSH from local)
ssh opc@130.162.167.220 "cd ~/AnkAi && git pull && docker compose -f docker-compose.prod.yml build && docker compose -f docker-compose.prod.yml up -d"
```

### View logs
```bash
ssh opc@130.162.167.220 "docker logs ankai-backend"
ssh opc@130.162.167.220 "docker logs ankai-anki"
ssh opc@130.162.167.220 "docker logs ankai-caddy"
```

### Restart services
```bash
ssh opc@130.162.167.220 "docker compose -f docker-compose.prod.yml restart"
```

### Sync Anki with AnkiWeb
```bash
ssh opc@130.162.167.220 "curl -s http://localhost:8765 -X POST -d '{\"action\": \"sync\", \"version\": 6}'"
```

### Test AnkiConnect
```bash
ssh opc@130.162.167.220 "docker exec ankai-anki curl -s http://localhost:8765 -X POST -d '{\"action\": \"version\", \"version\": 6}'"
```

---

## Recent Changes (2025-12-22)

1. **Article extraction improved** - Added `trafilatura` library for cleaner article text extraction, filters out boilerplate like "Image source", "This page requires JavaScript", etc.

2. **UI improvements** - Stats bar (comprehension, due, new, playback controls) is now sticky and responsive on mobile.

3. **AnkiConnect fix** - Addon files needed to be in `~/AnkAi/anki/addons21/2055492159/` (mounted via docker-compose), not in the main anki-data volume.

---

## Known Issues / TODO

1. **HTTPS not working** - DuckDNS had DNS issues with Let's Encrypt CAA lookup. Could retry later or use different DNS provider.

2. **ARM emulation** - Server is ARM but anki-desktop-docker is x86, running via QEMU emulation. Works but slower than native.

3. **Manual Anki sync** - Need to periodically sync Anki with AnkiWeb (via VNC or API call).

---

## Architecture Summary

```
User Browser
    │
    ▼
Caddy (:80/:443)
    │
    ├──/api/*──► Backend (FastAPI :8000)
    │                │
    │                ├──► AnkiConnect (:8765)
    │                │         │
    │                │         ▼
    │                │    Anki Desktop (VNC :3000)
    │                │         │
    │                │         ▼
    │                │    AnkiWeb (cloud sync)
    │                │
    │                └──► Groq API (LLM)
    │
    └──/*──► Frontend (nginx :80)
```
