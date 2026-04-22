#!/usr/bin/env bash
# Daily update script for RS-Paper-Hub
# Usage:
#   bash run_daily.sh          # default: arXiv API
#   bash run_daily.sh --web    # fallback: scrape arXiv HTML (when API is down)

set -e
cd "$(dirname "$0")"

MODE="api"
if [[ "$1" == "--web" ]]; then
  MODE="web"
fi

echo "========== RS-Paper-Hub Daily Update =========="
echo "$(date '+%Y-%m-%d %H:%M:%S')  [mode: $MODE]"
echo ""

# 1. Fetch latest papers (last 7 days)
echo "[1/3] Fetching latest papers..."
if [[ "$MODE" == "web" ]]; then
  python3 main_web.py --update
else
  python3 main.py --update
fi

# 2. Run full pipeline (clean + classify + tag + filter + trends)
echo ""
echo "[2/3] Running pipeline..."
python3 pipeline.py

# 3. Summary
echo ""
echo "[3/3] Done!"
echo "$(date '+%Y-%m-%d %H:%M:%S')"
