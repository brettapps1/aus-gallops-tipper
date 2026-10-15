#!/usr/bin/env python3
"""
Package FormFav Racing Intelligence Bulletin into a subscriber-ready product zip.
"""
import zipfile
import os
from pathlib import Path

DATE = "2026-10-08"
dir_path = Path(f"outputs/formfav/{DATE}")
dir_path.mkdir(parents=True, exist_ok=True)

bulletin_path = dir_path / f"AUS_RACES_PREDICTIONS_{DATE}.md"
sales_copy_path = dir_path / "racing_sales_copy.md"

sales_copy_content = f"""# 🐎 Fair Dinkum FormFav Racing Intelligence — {DATE} Daily Tier

Unlock professional-grade horse racing analytics, algorithmic barrier/weight trifecta selections, and global race card breakdowns.

## What's Included:
- **Full AU Meeting Cards:** Orange & York complete runner analysis, jockeys, trainers, barriers, and weights.
- **Algorithmic Trifecta Selections:** Boxed trifecta tips optimised via FormFav API metrics.
- **Global Track Coverage:** Access to AU, GB, IE, FR, ZA, TR, and JP meetings.

## Subscription Access
Delivered daily to your inbox and Obsidian vault. Stop guessing. Start trading on data.
"""

sales_copy_path.write_text(sales_copy_content)

zip_path = dir_path / f"formfav_racing_subscription_{DATE}.zip"
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    if bulletin_path.exists():
        zf.write(bulletin_path, f"race_predictions_{DATE}.md")
    zf.write(sales_copy_path, "sales_copy.md")

print(f"✅ Racing subscription package created: {zip_path} ({os.path.getsize(zip_path)} bytes)")
