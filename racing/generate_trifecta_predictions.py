#!/usr/bin/env python3
"""
Trifecta Prediction Engine for Australian Gallops (2026-09-30)
=============================================================
Analyzes runners from yesterday's form guides (Balaklava, Ballarat, Rosehill)
and generates simulated expert trifecta selections (1st, 2nd, 3rd) based on barrier, weight, and field positioning.
"""

import subprocess
import json
from pathlib import Path

TRACKS = ["balaklava", "ballarat", "rosehill"]
DATE = "2026-09-30"
OUTPUT_FILE = Path("trifecta_predictions_2026_09_30.md")

def run_formfav(cmd_args):
    cmd = ["python3", "formfav.py"] + cmd_args
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and res.stdout.strip():
        try:
            return json.loads(res.stdout)
        except Exception:
            return {"raw": res.stdout}
    return {}

def main():
    print(f"Generating Trifecta Predictions for {DATE}...")
    
    report = []
    report.append(f"# 🎯 Trifecta Predictions & Form Analysis — {DATE}\n")
    report.append("Generated via FormFav API & Trifecta Predictor Engine.\n")
    
    meetings_data = run_formfav(["meetings", DATE])
    
    for track in TRACKS:
        track_data = None
        for m in meetings_data.get("meetings", []):
            if m.get("slug") == track and m.get("country") == "au":
                track_data = m
                break
                
        if not track_data:
            continue
            
        report.append(f"\n## 🏟️ Track: {track_data.get('track', track.title())} (AU)\n")
        
        for r in track_data.get("races", []):
            rnum = r.get("raceNumber")
            rname = r.get("raceName", f"Race {rnum}")
            dist = r.get("distance", "N/A")
            cond = r.get("condition", "N/A")
            
            report.append(f"### Race {rnum}: {rname} ({dist} | {cond})")
            
            card = run_formfav(["race-card", DATE, track, str(rnum)])
            runners = card.get("runners", [])
            
            if runners:
                # Simple algorithmic heuristic for trifecta selection:
                # Select top 3 based on barrier advantage and weight balance
                sorted_runners = sorted(
                    runners, 
                    key=lambda x: (
                        int(x.get("barrier", 99)) if str(x.get("barrier", "")).isdigit() else 99, 
                        float(x.get("weight", 56.0)) if str(x.get("weight", "")).replace(".","").isdigit() else 56.0
                    )
                )
                
                sel1 = sorted_runners[0].get("horseName", "Runner A")
                sel2 = sorted_runners[1].get("horseName", "Runner B") if len(sorted_runners) > 1 else "Runner B"
                sel3 = sorted_runners[2].get("horseName", "Runner C") if len(sorted_runners) > 2 else "Runner C"
                
                report.append(f"- **1st (Win):** {sel1} (Barrier {sorted_runners[0].get('barrier', '-')}, Wt {sorted_runners[0].get('weight', '-')})")
                report.append(f"- **2nd (Place):** {sel2} (Barrier {sorted_runners[1].get('barrier', '-')}, Wt {sorted_runners[1].get('weight', '-')})")
                report.append(f"- **3rd (Show):** {sel3} (Barrier {sorted_runners[2].get('barrier', '-')}, Wt {sorted_runners[2].get('weight', '-')})")
                report.append(f"- *Trifecta Tip:* Box {sel1} / {sel2} / {sel3}\n")
            else:
                report.append("- *Predictions:* Field analysis pending runner weight distribution.\n")

    OUTPUT_FILE.write_text("\n".join(report))
    print(f"✅ Trifecta predictions saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
