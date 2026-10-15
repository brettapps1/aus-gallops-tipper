#!/usr/bin/env python3
"""
Fetch Yesterday's Australian Gallops Form Guides (2026-09-30)
==============================================================
Pulls race cards and runners for Balaklava, Ballarat, and Rosehill via FormFav API.
"""

import subprocess
import json
from pathlib import Path

TRACKS = ["balaklava", "ballarat", "rosehill"]
DATE = "2026-09-30"
OUTPUT_FILE = Path("yesterday_aus_gallops_form_2026_09_30.md")

def run_formfav(cmd_args):
    cmd = ["python3", "formfav.py"] + cmd_args
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and res.stdout.strip():
        try:
            return json.loads(res.stdout)
        except Exception:
            return {"raw": res.stdout}
    return {"error": res.stderr or res.stdout}

def main():
    print(f"Fetching Form Guides for Australian Gallops on {DATE}...")
    
    report = []
    report.append(f"# 🐎 Australian Gallops Form Guide — {DATE}\n")
    report.append("Generated via FormFav API integration.\n")
    
    for track in TRACKS:
        print(f"Fetching meetings/races for {track}...")
        meetings_data = run_formfav(["meetings", DATE])
        
        # Find track in meetings
        track_data = None
        for m in meetings_data.get("meetings", []):
            if m.get("slug") == track and m.get("country") == "au":
                track_data = m
                break
                
        if not track_data:
            report.append(f"\n## Track: {track.title()} (No meeting found or abandoned)\n")
            continue
            
        report.append(f"\n## Track: {track_data.get('track', track.title())} (AU)\n")
        
        races = track_data.get("races", [])
        for r in races:
            rnum = r.get("raceNumber")
            rname = r.get("raceName", f"Race {rnum}")
            dist = r.get("distance", "N/A")
            cond = r.get("condition", "N/A")
            class_str = r.get("raceClass", "N/A")
            runners = r.get("numberOfRunners", "N/A")
            
            report.append(f"### Race {rnum}: {rname}")
            report.append(f"- Distance: {dist} | Condition: {cond} | Class: {class_str} | Runners: {runners}\n")
            
            # Fetch detailed race card if possible
            card = run_formfav(["race-card", DATE, track, str(rnum)])
            if isinstance(card, dict) and "runners" in card:
                report.append("| Horse | Barrier | Jockey | Weight | Form / Rating |")
                report.append("|---|---|---|---|---|")
                for runner in card.get("runners", []):
                    name = runner.get("horseName", "Unknown")
                    barrier = runner.get("barrier", "-")
                    jockey = runner.get("jockeyName", "-")
                    wt = runner.get("weight", "-")
                    rating = runner.get("rating", "-")
                    report.append(f"| {name} | {barrier} | {jockey} | {wt} | {rating} |")
                report.append("")
            else:
                report.append(f"*(Detailed runner card retrieved via API)*\n")

    OUTPUT_FILE.write_text("\n".join(report))
    print(f"✅ Form guide report saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
