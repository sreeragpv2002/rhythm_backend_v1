# Base image
FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GRPC_DNS_RESOLVER=native \
    PORT=8000 \
    DENO_INSTALL=/root/.deno \
    PATH="/root/.deno/bin:${PATH}"

WORKDIR /app

# Install system dependencies (Node.js, npm, git, Deno curl, etc. for bgutil PO Token Provider)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    unzip \
    nodejs \
    npm \
    git \
    ca-certificates \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Deno (required for yt-dlp EJS JavaScript challenge solver)
RUN curl -fsSL https://deno.land/install.sh | sh

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Clone bgutil PO Token Provider and install the yt-dlp plugin
RUN git clone --depth 1 https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git /opt/bgutil && \
    mkdir -p /root/yt-dlp-plugins/bgutil-ytdlp-pot-provider && \
    cp -r /opt/bgutil/plugin/* /root/yt-dlp-plugins/bgutil-ytdlp-pot-provider/ && \
    mkdir -p /root/.yt-dlp/plugins/bgutil-ytdlp-pot-provider && \
    cp -r /opt/bgutil/plugin/* /root/.yt-dlp/plugins/bgutil-ytdlp-pot-provider/

# Build bgutil PO Token Provider HTTP server
WORKDIR /opt/bgutil/server
RUN npm ci && npx tsc

# Copy application source code
WORKDIR /app
COPY . .

# Ensure startup script is executable
RUN chmod +x /app/start.sh

# Expose default port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Start container: launches bgutil PO Token Provider on localhost:4416 + FastAPI on $PORT
CMD ["/app/start.sh"]
