FROM python:3.12-slim

WORKDIR /app

# System deps for audio inference (cf-voice real mode only)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 git \
    && rm -rf /var/lib/apt/lists/*

# GIT_TOKEN: Forgejo token for private circuitforge-core install.
# Passed at build time via compose.cloud.yml build.args — never baked into a layer.
ARG GIT_TOKEN

# Install public sibling + private circuitforge-core (token consumed here, not cached)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir \
      "git+https://${GIT_TOKEN}@git.opensourcesolarpunk.com/Circuit-Forge/circuitforge-core.git@main"

COPY pyproject.toml .
RUN pip install --no-cache-dir -e . --no-deps

COPY app/ app/

ENV CF_VOICE_MOCK=1
EXPOSE 8522

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8522"]
