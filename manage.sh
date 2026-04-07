#!/usr/bin/env bash
# manage.sh — Linnet dev management script
set -euo pipefail

CMD=${1:-help}
API_PORT=${LINNET_PORT:-8522}
FE_PORT=${LINNET_FRONTEND_PORT:-8521}

_check_env() {
  if [[ ! -f .env ]]; then
    echo "No .env found — copying .env.example"
    cp .env.example .env
  fi
}

case "$CMD" in
  start)
    _check_env
    echo "Starting Linnet API on :${API_PORT} (mock mode)…"
    CF_VOICE_MOCK=1 conda run -n cf uvicorn app.main:app \
      --host 0.0.0.0 --port "$API_PORT" --reload &
    echo "Starting Linnet frontend on :${FE_PORT}…"
    cd frontend && npm install --silent && npm run dev &
    echo "API: http://localhost:${API_PORT}"
    echo "UI:  http://localhost:${FE_PORT}"
    wait
    ;;

  stop)
    echo "Stopping Linnet processes…"
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    pkill -f "vite.*${FE_PORT}" 2>/dev/null || true
    echo "Stopped."
    ;;

  status)
    echo -n "API:      "
    curl -sf "http://localhost:${API_PORT}/health" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['status'])" || echo "not running"
    echo -n "Frontend: "
    curl -sf "http://localhost:${FE_PORT}" -o /dev/null && echo "running" || echo "not running"
    ;;

  test)
    _check_env
    CF_VOICE_MOCK=1 conda run -n cf python -m pytest tests/ -v "${@:2}"
    ;;

  logs)
    echo "Use 'docker compose logs -f' in Docker mode, or check terminal for dev mode."
    ;;

  docker-start)
    _check_env
    docker compose up -d
    echo "API: http://localhost:${API_PORT}"
    echo "UI:  http://localhost:${FE_PORT}"
    ;;

  docker-stop)
    docker compose down
    ;;

  open)
    xdg-open "http://localhost:${FE_PORT}" 2>/dev/null \
      || open "http://localhost:${FE_PORT}" 2>/dev/null \
      || echo "Open http://localhost:${FE_PORT} in your browser"
    ;;

  *)
    echo "Usage: $0 {start|stop|status|test|logs|docker-start|docker-stop|open}"
    ;;
esac
