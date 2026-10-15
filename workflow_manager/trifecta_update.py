#!/usr/bin/env python3
"""CLI: update trifecta.db from fetched FormFav JSON (backfill friendly).

Usage:
    python3 workflow_manager/trifecta_update.py --date 2026-09-28
    python3 workflow_manager/trifecta_update.py --date tomorrow
    python3 workflow_manager/trifecta_update.py --all   # all outputs/formfav/*/
    python3 workflow_manager/trifecta_update.py --stats
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from datetime import datetime, timedelta
from app.agents.trifecta_updater_agent import TrifectaUpdaterAgent
from app.services.trifecta_db import TrifectaDB
import json


def parse_date(s: str) -> str:
    if s.lower() == "tomorrow":
        return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    if s.lower() == "today":
        return datetime.now().strftime("%Y-%m-%d")
    datetime.strptime(s, "%Y-%m-%d")
    return s


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Update trifecta.db from FormFav JSON")
    p.add_argument("--date", default=None, help="YYYY-MM-DD | today | tomorrow")
    p.add_argument("--all", action="store_true", help="backfill every outputs/formfav/<date>/")
    p.add_argument("--stats", action="store_true", help="print DB stats and exit")
    args = p.parse_args()

    if args.stats:
        print(json.dumps(TrifectaDB().stats(), indent=2))
        sys.exit(0)

    if args.all:
        root = Path("outputs/formfav")
        dates = sorted([d.name for d in root.iterdir() if d.is_dir()])
        for d in dates:
            try:
                datetime.strptime(d, "%Y-%m-%d")
            except ValueError:
                continue
            agent = TrifectaUpdaterAgent(project_id=f"trifecta-{d}", date=d)
            if not (Path(f"outputs/formfav/{d}") / f"meetings_au_{d}.json").exists():
                print(f"SKIP {d}: no meetings_au file")
                continue
            res = agent.execute()
            print(json.dumps(res["data"], indent=2))
    else:
        date = parse_date(args.date or "tomorrow")
        agent = TrifectaUpdaterAgent(project_id=f"trifecta-{date}", date=date)
        res = agent.execute()
        print(json.dumps(res, indent=2))
        print(json.dumps(TrifectaDB().stats(), indent=2))
