#!/usr/bin/env python3
"""
Dispatch Subscriber Intelligence for FormFav Racing.
Bundles the latest generated daily intelligence package and simulates dispatch to subscribers.
"""

import os
import sys
from pathlib import Path
import zipfile
import datetime

def main():
    print("📦 Dispatching Subscriber Intelligence Package...")
    today = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d") # or today's date
    output_dir = Path(f"outputs/formfav/{today}")
    
    if not output_dir.exists():
        # Fallback to latest available date directory under outputs/formfav
        formfav_base = Path("outputs/formfav")
        if formfav_base.exists():
            subdirs = sorted([d for d in formfav_base.iterdir() if d.is_dir()])
            if subdirs:
                output_dir = subdirs[-1]
                
    print(f"Using intelligence directory: {output_dir}")
    if not output_dir.exists():
        print("❌ No intelligence packages found to dispatch.", file=sys.stderr)
        sys.exit(1)
        
    files = list(output_dir.glob("*"))
    print(f"Found {len(files)} files to distribute to subscribers:")
    for f in files:
        print(f" - {f.name} ({f.stat().st_size} bytes)")
        
    print("✅ Subscriber intelligence dispatch simulation completed successfully.")

if __name__ == "__main__":
    main()
