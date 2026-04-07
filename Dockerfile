FROM python:3.12-slim

WORKDIR /app

# System deps for audio inference (cf-voice real mode only)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY app/ app/

ENV CF_VOICE_MOCK=1
EXPOSE 8522

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8522"]
