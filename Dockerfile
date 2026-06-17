# ─── Stage 1: install Python dependencies ────────────────────────────────────
FROM python:3.12-slim AS deps

WORKDIR /build

# Install only runtime dependencies (no dev extras)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ─── Stage 2: production image ────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Copy installed site-packages and scripts from deps stage
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application source
COPY app/ ./app/
COPY pyproject.toml README.md ./

# Register the CLI entry point without reinstalling any dependency
RUN pip install --no-cache-dir --no-deps -e .

# Non-root user — principle of least privilege
RUN addgroup --system app && \
    adduser --system --ingroup app --no-create-home app && \
    chown -R app:app /app
USER app

# ─── Runtime defaults ─────────────────────────────────────────────────────────
# Cloud Run injects PORT automatically; MCP_HTTP_PORT is the local fallback.
# NODE_ENV and LOG_LEVEL are overridable at deploy time.
ENV NODE_ENV=production \
    LOG_LEVEL=info \
    EASYPOST_MODE=production \
    MCP_HTTP_HOST=0.0.0.0 \
    MCP_HTTP_PORT=8080

EXPOSE 8080

# Docker-native health check (used by docker compose / local testing).
# Cloud Run uses its own startup/liveness probes — configure those separately.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c \
        "import urllib.request, os; \
         port = os.environ.get('PORT', os.environ.get('MCP_HTTP_PORT', '8080')); \
         urllib.request.urlopen(f'http://localhost:{port}/health', timeout=4)" \
    || exit 1

# Start in HTTP mode — the transport selection is the only runtime difference
# between local STDIO usage and this cloud deployment.
CMD ["easypost-mcp", "start", "--mode", "http"]
