#!/bin/bash
# Daily FormFav Aus Gallops fetch + booklets + trifecta.db update
# Runs: fetch tomorrow (Sydney) -> combined PDF -> per-meeting PDFs -> trifecta.db
# Logs: logs/formfav_daily_<DATE>.log
set -u

# Resolve repo root from script location so the script works from any cwd/user.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.." || exit 1

# Load env (FORMFAV_API_KEY lives in project .env or ~/.env)
if [ -f .env ]; then set -a; . ./.env 2>/dev/null; set +a; fi
if [ -z "${FORMFAV_API_KEY:-}" ]; then
  ENV_FILE="${FORMFAV_ENV_FILE:-$HOME/.env}"
  if [ -f "$ENV_FILE" ]; then
    # f2- keeps any '=' inside the value; strip surrounding quotes and CR.
    _ff_key=$(grep -m1 '^FORMFAV_API_KEY=' "$ENV_FILE" | cut -d= -f2- | tr -d '\r' | sed -e 's/^["'"'"']//' -e 's/["'"'"']$//')
    if [ -n "$_ff_key" ]; then export FORMFAV_API_KEY="$_ff_key"; fi
  fi
fi

DATE=$(TZ=Australia/Sydney date -d tomorrow +%F)
LOG="logs/formfav_daily_${DATE}.log"
mkdir -p logs outputs/formfav data

{
echo "=== daily_formfav_fetch $DATE $(date -u +%FT%TZ) ==="
echo "Step 1/7: fetch AU gallops forms"
python3 workflow_manager/formfav_gallops_cli.py --date "$DATE" --no-predictions
echo "Step 2/7: combined booklet"
python3 build_form_booklet.py "$DATE"
echo "Step 3/7: per-meeting booklets"
python3 build_meeting_booklets.py "$DATE"
echo "Step 4/7: trifecta picks (1st/2nd/3rd for every race) + PDF"
# build_trifecta_agent.py emits MD/CSV/JSON and also calls build_trifecta_pdf,
# so the booklet is produced here without a separate step. The PDF is
# best-effort: a reportlab failure warns but does not lose the picks.
python3 build_trifecta_agent.py "$DATE"
echo "Step 5/7: trifecta.db update"
python3 workflow_manager/trifecta_update.py --date "$DATE"
# Picks are written at step 4, BEFORE races are ingested here, so their race_id
# is NULL on a cold run. Now that races exist, link them. Idempotent, and a
# no-op if the step-4 re-run below already resolved them.
echo "      link picks -> races"
python3 backfill_pick_race_ids.py --date "$DATE" || echo "  warn: race_id backfill failed (continuing)"
echo "Step 6/7: market prices (if a Sportsbet paste is staged)"
# Market prices cannot be scraped: every free AU odds source is behind a bot
# wall or a paid tier (FormFav /v1/prices is Premium). The supported path is
# to paste the field page to MARKET_PASTE_DIR/<date>-<venue>.txt before this
# job runs, and the parser turns it into the price feed the model reads.
#
# stage_market.py does the parse AND verifies the prices are genuinely
# pre-race. It exits non-zero if any race fell back to a post-race "sp",
# which is a leak -- the model being told the answer. Check the exit code
# rather than assuming the paste was usable.
PASTE_DIR="${MARKET_PASTE_DIR:-$PWD/outputs/market_paste}"
if [ -d "$PASTE_DIR" ]; then
  shopt -s nullglob
  for f in "$PASTE_DIR/$DATE"-*.txt; do
    venue=$(basename "$f" .txt); venue=${venue#"$DATE-"}
    echo "  staging $venue"
    python3 stage_market.py "$DATE" "$venue" --in "$f" || \
      echo "  warn: $venue odds incomplete or leaking (see report above)"
  done
else
  echo "  no paste dir at $PASTE_DIR; skipping"
fi
# Rebuild the picks now that any prices have landed, so the blend is applied.
python3 build_trifecta_agent.py "$DATE"
echo "Step 7/7: combined Google Doc (form guide + trifecta picks)"
# Best-effort: needs the googledocs Composio connection to be ACTIVE. A
# failure here must not fail the fetch, so it is guarded.
if composio connections list 2>/dev/null | grep -q '"googledocs"'; then
  python3 build_daily_doc.py "$DATE" || echo "  warn: Google Doc build failed (continuing)"
else
  echo "  skip: googledocs connection not active"
fi
echo "=== done $DATE ==="
ls -lh outputs/formfav/"$DATE"/*.pdf outputs/formfav/"$DATE"/TRIFECTA_"$DATE".md
} >> "$LOG" 2>&1

echo "Logged to $LOG"
tail -n 15 "$LOG"
