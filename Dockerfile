FROM node:20-slim

# Install Python 3 + pip + venv
RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-venv --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps into an isolated venv (avoids system-package conflicts)
COPY optimate/requirements-deploy.txt optimate/requirements-deploy.txt
RUN python3 -m venv /app/venv && \
    /app/venv/bin/pip install --quiet --no-cache-dir -r optimate/requirements-deploy.txt

# Install Node deps
COPY backend/package*.json backend/
RUN cd backend && npm install --omit=dev

# Copy source
COPY backend/ backend/
COPY optimate/ optimate/

# Bake OptiMATE paths — no env vars needed in Render dashboard for these
ENV OPTIMATE_PYTHON=/app/venv/bin/python
ENV OPTIMATE_DIR=/app/optimate
ENV PORT=3000

EXPOSE 3000

CMD ["node", "backend/server.js"]
