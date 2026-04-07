#!/usr/bin/env bash
# manage.sh — Linnet dev/demo/cloud management script
set -euo pipefail

CMD=${1:-help}
PROFILE=${2:-dev}  # dev | demo | cloud
API_PORT=${LINNET_PORT:-8522}
FE_PORT=${LINNET_FRONTEND_PORT:-8521}

# ── Helpers ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[linnet]${NC} $*"; }
warn()  { echo -e "${YELLOW}[linnet]${NC} $*"; }
error() { echo -e "${RED}[linnet]${NC} $*" >&2; exit 1; }

_check_env() {
  if [[ ! -f .env ]]; then
    warn "No .env found — copying .env.example"
    cp .env.example .env
  fi
}

_compose_cmd() {
  # Returns the correct compose file flags for a given profile
  case "$1" in
    demo)  echo "-f compose.demo.yml  -p linnet-demo" ;;
    cloud) echo "-f compose.cloud.yml -p linnet-cloud" ;;
    test)  echo "-f compose.test.yml" ;;
    dev)   echo "-f compose.yml" ;;
    *)     error "Unknown profile: $1. Use dev|demo|cloud|test." ;;
  esac
}

# ── Commands ──────────────────────────────────────────────────────────────────
case "$CMD" in

  start)
    _check_env
    if [[ "$PROFILE" == "dev" ]]; then
      info "Starting Linnet API on :${API_PORT} (mock mode, dev)…"
      CF_VOICE_MOCK=1 conda run -n cf uvicorn app.main:app \
        --host 0.0.0.0 --port "$API_PORT" --reload &
      info "Starting Linnet frontend on :${FE_PORT}…"
      cd frontend && npm install --silent && npm run dev &
      info "API: http://localhost:${API_PORT}"
      info "UI:  http://localhost:${FE_PORT}"
      wait
    else
      FLAGS=$(_compose_cmd "$PROFILE")
      info "Starting Linnet ($PROFILE profile)…"
      # shellcheck disable=SC2086
      docker compose $FLAGS up -d --build
      case "$PROFILE" in
        demo)  info "Frontend: http://localhost:8524" ;;
        cloud) info "Frontend: http://localhost:8527 → menagerie.circuitforge.tech/linnet" ;;
      esac
    fi
    ;;

  stop)
    if [[ "$PROFILE" == "dev" ]]; then
      info "Stopping Linnet dev processes…"
      pkill -f "uvicorn app.main:app" 2>/dev/null || true
      pkill -f "vite" 2>/dev/null || true
    else
      FLAGS=$(_compose_cmd "$PROFILE")
      # shellcheck disable=SC2086
      docker compose $FLAGS down
    fi
    info "Stopped ($PROFILE)."
    ;;

  restart)
    "$0" stop  "$PROFILE"
    "$0" start "$PROFILE"
    ;;

  status)
    case "$PROFILE" in
      dev)
        echo -n "API:      "
        curl -sf "http://localhost:${API_PORT}/health" 2>/dev/null \
          | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['status'], '|', d.get('mode','dev'))" \
          || echo "not running"
        echo -n "Frontend: "
        curl -sf "http://localhost:${FE_PORT}" -o /dev/null && echo "running" || echo "not running"
        ;;
      demo)
        echo -n "Demo API:  "; curl -sf "http://localhost:8523/health" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['status'])" || echo "not running"
        echo -n "Demo Web:  "; curl -sf "http://localhost:8524" -o /dev/null && echo "running" || echo "not running"
        ;;
      cloud)
        echo -n "Cloud API: "; curl -sf "http://localhost:8522/health" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['status'])" || echo "not running"
        echo -n "Cloud Web: "; curl -sf "http://localhost:8527" -o /dev/null && echo "running" || echo "not running"
        ;;
    esac
    ;;

  test)
    _check_env
    if [[ "$PROFILE" == "dev" ]]; then
      info "Running test suite (local)…"
      CF_VOICE_MOCK=1 conda run -n cf python -m pytest tests/ -v "${@:3}"
    else
      info "Running test suite (Docker)…"
      docker compose -f compose.test.yml run --rm linnet-test "${@:3}"
    fi
    ;;

  logs)
    if [[ "$PROFILE" == "dev" ]]; then
      warn "Dev mode: check terminal output."
    else
      FLAGS=$(_compose_cmd "$PROFILE")
      SERVICE=${3:-}
      # shellcheck disable=SC2086
      docker compose $FLAGS logs -f $SERVICE
    fi
    ;;

  build)
    info "Building Docker images ($PROFILE)…"
    FLAGS=$(_compose_cmd "$PROFILE")
    # shellcheck disable=SC2086
    docker compose $FLAGS build
    info "Build complete."
    ;;

  open)
    case "$PROFILE" in
      demo)  URL="http://localhost:8524" ;;
      cloud) URL="http://localhost:8527" ;;
      *)     URL="http://localhost:${FE_PORT}" ;;
    esac
    xdg-open "$URL" 2>/dev/null || open "$URL" 2>/dev/null || info "Open $URL in your browser"
    ;;

  help|*)
    echo ""
    echo "  Usage: $0 <command> [profile]"
    echo ""
    echo "  Commands:"
    echo -e "    ${GREEN}start${NC}    [profile]   Start API + frontend"
    echo -e "    ${GREEN}stop${NC}     [profile]   Stop services"
    echo -e "    ${GREEN}restart${NC}  [profile]   Stop then start"
    echo -e "    ${GREEN}status${NC}   [profile]   Check running services"
    echo -e "    ${GREEN}test${NC}     [profile]   Run pytest suite"
    echo -e "    ${GREEN}logs${NC}     [profile]   Tail logs (Docker profiles only)"
    echo -e "    ${GREEN}build${NC}    [profile]   Build Docker images"
    echo -e "    ${GREEN}open${NC}     [profile]   Open UI in browser"
    echo ""
    echo "  Profiles:"
    echo "    dev     (default) Local uvicorn + Vite dev server, mock mode"
    echo "    demo    Docker: DEMO_MODE=true, port 8524"
    echo "    cloud   Docker: CLOUD_MODE=true, port 8527 → menagerie.circuitforge.tech/linnet"
    echo "    test    Docker: pytest suite, hermetic"
    echo ""
    echo "  Examples:"
    echo "    $0 start                  # dev mode"
    echo "    $0 start demo             # demo stack"
    echo "    $0 test                   # local pytest"
    echo "    $0 test docker            # pytest in Docker"
    echo "    $0 logs demo              # demo logs"
    echo ""
    ;;
esac
