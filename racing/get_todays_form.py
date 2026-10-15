import os
from pathlib import Path
import subprocess

for env_path in [Path.home() / ".env", Path(".env"), Path("fair-dinkum-publishing-agent-workflowz/.env")]:
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("FORMFAV_API_KEY="):
                os.environ["FORMFAV_API_KEY"] = line.split("=", 1)[1].strip("'\" ")

print("API Key found:", bool(os.environ.get("FORMFAV_API_KEY")))
result = subprocess.run(["python3", "formfav.py", "meetings", "2026-10-10"], capture_output=True, text=True)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
