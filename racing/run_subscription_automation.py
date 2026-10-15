#!/usr/bin/env python3
"""
Run Subscription Automation for FormFav Racing Intelligence.
Executes the daily fetch script, checks logs, and ensures robust error handling.
"""

import os
import subprocess
import sys
from pathlib import Path

def main():
    print("🚀 Starting FormFav Subscription Automation Runner...")
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent
    fetch_script = repo_root / "workflow_manager" / "daily_formfav_fetch.sh"
    
    if not fetch_script.exists():
        print(f"Error: Fetch script not found at {fetch_script}", file=sys.stderr)
        sys.exit(1)
        
    print(f"Executing fetch script: {fetch_script}")
    result = subprocess.run(["bash", str(fetch_script)], cwd=repo_root, capture_output=True, text=True)
    
    print("STDOUT:")
    print(result.stdout)
    
    if result.returncode != 0:
        print("STDERR:")
        print(result.stderr, file=sys.stderr)
        print("❌ Daily fetch script encountered errors.", file=sys.stderr)
        sys.exit(result.returncode)
    else:
        print("✅ Daily FormFav subscription automation completed successfully.")

if __name__ == "__main__":
    main()
