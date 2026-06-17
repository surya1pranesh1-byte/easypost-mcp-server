# EasyPost MCP Server (Python)

A production-quality Python implementation of the EasyPost Model Context Protocol (MCP) server.

## Requirements

- Python 3.12+
- An EasyPost API key ([sign up free](https://www.easypost.com/signup))

## Quick Start

```bash
# 1. Install dependencies
pip install -e ".[dev]"

# 2. Copy and fill in your environment variables
cp .env.example .env
# Edit .env and set EASYPOST_API_KEY=...

# 3. Start the server (stdio mode — for MCP clients like Claude Desktop)
easypost-mcp start

# Or start in HTTP mode
easypost-mcp start --mode http --port 8080
```

## CLI Reference

```
easypost-mcp start [OPTIONS]

Options:
  --api-key TEXT          EasyPost API key (or set EASYPOST_API_KEY)
  --mode TEXT             Transport: stdio or http (default: stdio)
  --easypost-mode TEXT    EasyPost env: sandbox or production (default: sandbox)
  --log-level TEXT        Log level: trace, debug, info, warn, error (default: info)
  --port INTEGER          HTTP port (default: 8080)
  --host TEXT             HTTP bind host (default: 0.0.0.0)
  --timeout-ms INTEGER    EasyPost timeout in ms (default: 30000)
  --retry-attempts INT    Retry attempts (default: 2)
  --rate-limit INTEGER    Tool calls/minute (default: 60)
```

## Available MCP Tools

### Shipments
| Tool | Description |
|---|---|
| `create_shipment` | Create a shipment and get carrier rates |
| `buy_shipping_label` | Purchase a shipping label (requires confirmation) |
| `get_shipment` | Retrieve shipment by ID |
| `list_shipments` | List shipments with pagination |
| `estimate_rates` | Get rates without buying |
| `cancel_shipment` | Cancel/void a shipment (requires confirmation) |
| `refund_shipment` | Request a label refund (requires confirmation) |
| `insure_shipment` | Add insurance to a shipment |

### Tracking
| Tool | Description |
|---|---|
| `track_package` | Create/refresh a tracker |
| `get_tracking_history` | Get tracking events |

### Addresses
| Tool | Description |
|---|---|
| `verify_address` | Verify and normalize a shipping address |
| `create_address` | Create an EasyPost address object |

### Returns
| Tool | Description |
|---|---|
| `create_return_label` | Create a return label |

### Pickups
| Tool | Description |
|---|---|
| `schedule_pickup` | Schedule a carrier pickup (requires confirmation) |
| `cancel_pickup` | Cancel a pickup (requires confirmation) |

### Batches
| Tool | Description |
|---|---|
| `create_batch` | Create a batch of shipments |
| `buy_batch` | Buy labels for a batch (requires confirmation) |
| `batch_status` | Get batch processing status |

### Orders
| Tool | Description |
|---|---|
| `create_order` | Create a multi-shipment order |
| `get_order` | Retrieve an order by ID |

### Resources
| Tool | Description |
|---|---|
| `get_carriers` | List supported carriers |
| `validate_carrier` | Validate a carrier code |
| `validate_service` | Validate a carrier/service combination |

## HTTP Transport

When running with `--mode http`, the server uses the configured EasyPost API key directly and exposes:

- `POST /mcp` + `GET /mcp` + `DELETE /mcp` — MCP Streamable HTTP endpoints
- `GET /health` — liveness probe → `{"status": "UP"}`
- `GET /ready` — readiness probe → `{"status": "READY"}` (503 if API key is missing)

---

## GCP Cloud Run Deployment

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        EasyPost MCP Server                       │
│                                                                   │
│   ┌─────────────┐          ┌──────────────────────────────────┐  │
│   │    STDIO    │          │        Streamable HTTP           │  │
│   │  Transport  │          │           Transport              │  │
│   │             │          │                                  │  │
│   │  Local dev  │          │  POST /mcp  ─── MCP session      │  │
│   │  Claude     │          │  GET  /mcp  ─── SSE stream       │  │
│   │  Desktop    │          │  DELETE /mcp ── session close     │  │
│   └─────────────┘          │                                  │  │
│                            │  GET /health   ── liveness       │  │
│                            │  GET /ready    ── readiness      │  │
│                            │  POST /mcp     ── tool calls     │  │
│                            │  GET /mcp      ── session stream │  │
│                            │  DELETE /mcp   ── session close  │  │
│                            └──────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
            │                              │
            │                             GCP Cloud Run
            │                    ┌──────────────────────────┐
            │                    │                          │
            ▼                    │  ┌────────────────────┐  │
   Claude Desktop                │  │  MCP Connector     │  │
   (local stdio)                 │  │  (external users)  │  │
                                 │  └────────────────────┘  │
                                 │                          │
                                 │  ┌────────────────────┐  │
                                 │  │  EasyPost          │  │
                                 │  │  Assistant         │  │
                                 │  │  (internal AI)     │  │
                                 │  └────────────────────┘  │
                                 └──────────────────────────┘
```

### Prerequisites

- [gcloud CLI](https://cloud.google.com/sdk/docs/install) authenticated (`gcloud auth login`)
- Docker installed and running
- A GCP project with billing enabled

### Quick deploy

```bash
export GCP_PROJECT_ID=my-gcp-project
export EASYPOST_API_KEY=EZAK...

bash deploy.sh
```

`deploy.sh` runs all phases automatically:
1. Enables required GCP APIs
2. Creates Artifact Registry repository
3. Stores the EasyPost key in Secret Manager
4. Builds and pushes Docker image
5. Deploys to Cloud Run
6. Creates log-based metrics in Cloud Monitoring

### Manual deployment

#### 1. Enable GCP services

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  --project=MY_PROJECT
```

#### 2. Create Artifact Registry repository

```bash
gcloud artifacts repositories create easypost-mcp \
  --repository-format=docker \
  --location=us-central1 \
  --description="EasyPost MCP Server images"

gcloud auth configure-docker us-central1-docker.pkg.dev
```

#### 3. Store secrets in Secret Manager

```bash
# Never commit secrets. Store them in Secret Manager.
echo -n "EZAK..." | gcloud secrets create easypost-api-key --data-file=-
```

#### 4. Build and push the image

```bash
IMAGE=us-central1-docker.pkg.dev/MY_PROJECT/easypost-mcp/easypost-mcp:latest

docker build -t "$IMAGE" .
docker push "$IMAGE"
```

Or use Cloud Build (no local Docker required):

```bash
gcloud builds submit --config cloudbuild.yaml \
  --substitutions=_REGION=us-central1,_REPO=easypost-mcp,_SERVICE=easypost-mcp
```

#### 5. Deploy to Cloud Run

```bash
gcloud run deploy easypost-mcp \
  --image="$IMAGE" \
  --region=us-central1 \
  --port=8080 \
  --cpu=1 \
  --memory=512Mi \
  --concurrency=80 \
  --min-instances=1 \
  --max-instances=10 \
  --timeout=60s \
  --set-secrets="EASYPOST_API_KEY=easypost-api-key:latest" \
  --set-env-vars="NODE_ENV=production,LOG_LEVEL=info,EASYPOST_MODE=production" \
  --allow-unauthenticated
```

#### 6. Resource sizing rationale

| Parameter | Value | Why |
|---|---|---|
| `--cpu` | 1 | Sufficient for async Python + EasyPost SDK; increase to 2 if p95 latency > 2 s |
| `--memory` | 512 Mi | Covers Python runtime + in-memory session store |
| `--concurrency` | 80 | Uvicorn handles requests concurrently inside one process; 80 is the Cloud Run default |
| `--min-instances` | 1 | Keeps one instance warm; eliminates cold-start latency for the EasyPost Assistant |
| `--max-instances` | 10 | Hard cap to control costs; adjust to traffic profile |
| `--timeout` | 60 s | Covers the slowest EasyPost operations (batch label generation) |

Set `--min-instances=0` to eliminate idle costs when cold starts (~1–2 s) are acceptable.

### Secret Manager configuration

| Secret name | Value | Notes |
|---|---|---|
| `easypost-api-key` | EasyPost production API key (`EZAK...`) | Never set as plain env var |

Secrets are injected at container startup as environment variables via `--set-secrets`. They never appear in Cloud Run configuration or logs.

### Monitoring and logging

Cloud Run automatically exports container metrics (CPU, memory, request count, request latency) to Cloud Monitoring. Structured JSON logs from `structlog` are captured by Cloud Logging.

**Log-based metrics** created by `deploy.sh --monitoring`:

| Metric | Filter | Use |
|---|---|---|
| `easypost_mcp_tool_calls` | `event="MCP tool called"` | Tool invocation rate per tool |
| `easypost_mcp_tool_errors` | `event="Tool execution failed"` | Error rate per tool |
| `easypost_mcp_tool_latency` | `event="MCP tool completed"` | Latency distribution (ms) |

**Recommended alerts** (create in Cloud Monitoring):
- Error rate > 5% over 5 min → PagerDuty / email
- p95 latency > 5 000 ms over 5 min → investigation
- Instance count hits `max-instances` → scale review

**Error Reporting**: Cloud Error Reporting auto-detects Python exceptions from Cloud Logging — no additional configuration required.

### EasyPost Assistant integration

For an internal AI assistant that needs to call the cloud-hosted MCP server:

```python
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def get_mcp_client(service_url: str):
    timeout = httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0)
    limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)

    async with streamablehttp_client(
        f"{service_url}/mcp",
        timeout=timeout,
        limits=limits,
    ) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session

async def track_shipment(tracking_code: str) -> dict:
    async with get_mcp_client("https://<cloud-run-url>") as mcp:
        result = await mcp.call_tool("track_package", {"tracking_code": tracking_code})
        return result
```

**Connection recommendations:**

| Setting | Value | Reason |
|---|---|---|
| Connect timeout | 5 s | Cloud Run cold start is < 2 s with min=1 |
| Read timeout | 60 s | Matches Cloud Run request timeout |
| Max connections | 10 | Enough for burst; avoid exhausting Cloud Run concurrency |
| Retry attempts | 3 | With exponential back-off on 429 / 503 |
| Retry back-off | 1 s, 2 s, 4 s | Avoids thundering herd |

### Production deployment checklist

- [ ] `EASYPOST_API_KEY` stored in Secret Manager (not as env var)
- [ ] `NODE_ENV=production` and `EASYPOST_MODE=production` confirmed in Cloud Run env
- [ ] `LOG_LEVEL=info` (not `debug`) in production
- [ ] `--min-instances=1` to keep the assistant's latency predictable
- [ ] Cloud Run startup probe configured: `GET /health`, initial delay 10 s
- [ ] Cloud Run liveness probe configured: `GET /health`, period 30 s
- [ ] Log-based metrics created (`deploy.sh --monitoring`)
- [ ] Alert policies created for error rate and latency
- [ ] Cloud Build trigger connected to `main` branch for CI/CD
- [ ] Container image tags use git SHA (not `latest`) in production
- [ ] Artifact Registry vulnerability scanning enabled
- [ ] Service account has only `roles/secretmanager.secretAccessor` (principle of least privilege)

## Project Structure

```
app/
├── config/          # Pydantic Settings configuration
├── server/          # MCP server factory + transports (stdio, HTTP)
├── tools/           # Tool registry, definitions per domain
├── services/        # Business logic (shipments, addresses, tracking, …)
├── clients/         # EasyPost API client with retry + timeout
├── resources/       # Carrier/service/country resource cache
├── pipeline/        # Execution pipeline: validation, elicitation, anti-hallucination
├── schemas/         # Pydantic v2 input schemas per domain
├── middleware/       # Rate limiter and transport middleware
├── adapters/        # EasyPost response mappers
├── elicitation/     # Fallback responses, field catalog
├── audit/           # Audit logger
├── validators/      # Input validation + anti-hallucination checks
├── utils/           # Correlation IDs, sanitize, token generation
├── exceptions/      # Typed application errors
└── constants/       # Tool categories, risk levels
```

## Key Design Decisions

- **Pydantic v2** for all input validation (replaces Zod)
- **structlog** for structured JSON logging to stderr (replaces Pino)
- **FastAPI + Uvicorn** for HTTP transport (replaces Express)
- **click** for the CLI (replaces Commander.js)
- **asyncio.to_thread()** wraps the synchronous EasyPost Python SDK
- **httpx** for async HTTP calls to EasyPost
- **Levenshtein fuzzy matching** for carrier/service suggestions (pure Python, no external deps)
- **Anti-hallucination validation** rejects placeholder/garbage input before sending to EasyPost
- **Workflow state** carries partial inputs across multi-turn elicitation flows
- **Idempotency store** prevents duplicate purchases on retried calls
