# Render Key Extractor Service

Production-ready service to automate Render account confirmation links and extract Render API keys with Tor IP rotation.

## Features

- **Automated Key Extraction**: Accepts email confirmation links (Postmark tracking URLs or direct Render activation URLs), validates the session via headless Chromium, and extracts the full Render API key (`rnd_...`).
- **Render REST API Verification**: Automatically verifies generated keys against `https://api.render.com/v1/owners` to fetch workspace owner ID, workspace name, and account email.
- **Tor Anonymity & IP Rotation**:
  - Full Tor SOCKS5 proxy integration (`socks5://127.0.0.1:9050`).
  - ON / OFF toggle on Web UI and API.
  - On-demand circuit rotation via Tor ControlPort (`SIGNAL NEWNYM`) to switch exit IPs and avoid rate limits or IP blocking.
- **Dual-Method Ping / Health Check**:
  - `/ping` and `/health` endpoints support both `GET` and `HEAD` requests.
- **Professional Web UI**:
  - Clean responsive dashboard on port `8090`.
  - 1-click key copying, live progress status, Tor circuit rotation button, and SQLite history tracking.
- **Systemd Background Service**: Runs as a daemon under systemd (`render-key-service.service`).

## Project Structure

```text
/home/ubuntu/render-key-service/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application & lifecycle
│   ├── config.py            # Environment configurations
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py        # /ping, /health, /api/extract, /api/tor/status, /api/tor/rotate, /api/history
│   ├── services/
│   │   ├── __init__.py
│   │   ├── extractor.py     # Playwright automation & key extraction
│   │   ├── tor_manager.py   # Tor SOCKS5 & ControlPort circuit rotation
│   │   └── db.py            # SQLite history persistence
│   ├── static/
│   │   ├── css/style.css    # Responsive dark UI styles
│   │   └── js/app.js        # Frontend logic & API interaction
│   └── templates/
│       └── index.html       # Web Dashboard HTML
├── data/
│   └── keys.db              # SQLite extraction database
├── requirements.txt         # Dependencies
├── run.sh                   # Startup runner
└── render-key-service.service # Systemd service unit
```

## API Endpoints

### 1. Health / Ping (Supports GET and HEAD)
- `GET /ping` or `HEAD /ping`: Fast health check.
- `GET /health` or `HEAD /health`: Detailed status including Tor network status and exit IP.

### 2. Extract Key
- `POST /api/extract`
  ```json
  {
    "url": "https://track.pstmrk.it/3s/dashboard.render.com...",
    "name": "MyDeployKey",
    "use_tor": true,
    "rotate_before": true
  }
  ```

### 3. Tor Management
- `GET /api/tor/status`: Returns current Direct IP and Tor Exit IP.
- `POST /api/tor/rotate`: Sends `SIGNAL NEWNYM` to obtain a fresh Tor exit IP.

### 4. History
- `GET /api/history`: List recent extractions with status and masked keys.
