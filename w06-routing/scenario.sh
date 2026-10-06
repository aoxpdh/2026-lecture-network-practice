#!/usr/bin/env bash
# Week 6 OSPF lab: up | routes | measure | cut | restore | cost | down
# measure records five experiments and restores interfaces/costs afterwards.
set -euo pipefail
cd "$(dirname "$0")/.."
case "${1:-}" in
  up)
    docker compose --profile routing up -d r1 r2 r3
    python3 w06-routing/measure_ospf.py wait
    ;;
  routes|measure|cut|restore|cost)
    python3 w06-routing/measure_ospf.py "$1"
    ;;
  down)
    # Stop only lab routers, never the unrelated default lab service.
    docker compose --profile routing stop r1 r2 r3
    ;;
  *)
    echo "Usage: bash scenario.sh {up|routes|measure|cut|restore|cost|down}"
    exit 2
    ;;
esac
