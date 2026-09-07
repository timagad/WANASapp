#!/usr/bin/env bash
# WANAS — one command to a working demo. POSIX counterpart of demo.ps1.
#
#   ./scripts/demo.sh              start
#   ./scripts/demo.sh --rebuild    force a rebuild of the images
#   ./scripts/demo.sh --down       stop everything
set -euo pipefail

cd "$(dirname "$0")/.."

cyan=$'\033[36m'; green=$'\033[32m'; yellow=$'\033[33m'; red=$'\033[31m'; off=$'\033[0m'
step() { printf '\n%s=> %s%s\n' "$cyan" "$1" "$off"; }
ok()   { printf '   %s%s%s\n' "$green" "$1" "$off"; }
warn() { printf '   %s%s%s\n' "$yellow" "$1" "$off"; }
fail() { printf '   %s%s%s\n' "$red" "$1" "$off"; }

if [ "${1:-}" = "--down" ]; then
  step "Stopping WANAS"
  docker compose down
  ok "Stopped. Data is preserved in the wanas_db volume."
  exit 0
fi

step "Checking Docker"
if ! engine=$(docker info --format '{{.ServerVersion}}' 2>/dev/null); then
  fail "Docker engine is not reachable."
  echo
  echo "   Start Docker Desktop (or your daemon) and run this again."
  echo "   On Windows, if its Linux backend has no WSL distribution:  wsl --install"
  exit 1
fi
ok "Docker engine $engine"

step "Checking configuration"
if [ ! -f .env ]; then
  cp .env.example .env
  ok "Created .env from .env.example"
else
  ok ".env present"
fi

if grep -qE '^[[:space:]]*ANTHROPIC_API_KEY[[:space:]]*=[[:space:]]*[^[:space:]]' .env; then
  ok "ANTHROPIC_API_KEY set - the guide will call Claude"
else
  warn "No ANTHROPIC_API_KEY - the guide runs the offline grounded provider."
  warn "That is a supported mode, not a failure: answers are composed from"
  warn "the heritage corpus and every one still carries its sources."
fi

step "Starting Postgres, Redis, API and web"
if [ "${1:-}" = "--rebuild" ]; then
  docker compose up -d --build
else
  docker compose up -d
fi

step "Waiting for the API (it seeds the database on first boot)"
health=""
for _ in $(seq 1 90); do
  if health=$(curl -fsS http://localhost:8000/health 2>/dev/null); then break; fi
  sleep 2
done
if [ -z "$health" ]; then
  fail "API did not come up in 3 minutes."
  echo "   Look at the logs:  docker compose logs api --tail 60"
  exit 1
fi
ok "API healthy - $health"

step "Waiting for the web app"
web_up=""
for _ in $(seq 1 45); do
  if curl -fsS -o /dev/null http://localhost:3000/fr 2>/dev/null; then web_up=1; break; fi
  sleep 2
done
if [ -n "$web_up" ]; then ok "Web app ready"; else warn "Web app slow to start - try http://localhost:3000 shortly"; fi

cat <<'BANNER'

  WANAS is running
  ------------------------------------------------------
  App          http://localhost:3000    (French)
               http://localhost:3000/ar (Arabic, RTL)
               http://localhost:3000/dz (Darija, RTL)
  API docs     http://localhost:8000/docs

  Demo accounts - password: wanas-demo-2026
    visiteur@wanas.dz   traveller   - itineraries, bookings, orders
    artisan@wanas.dz    artisan     - publish a product
    office@wanas.dz     institution - the anonymised dashboard

  Walkthrough  docs/demo-script.md  (4 minutes)
  Stop         ./scripts/demo.sh --down
  ------------------------------------------------------

BANNER
