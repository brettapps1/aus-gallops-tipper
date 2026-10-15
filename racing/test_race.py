import os
from pathlib import Path
import httpx

env_path = Path.home() / ".env"
if env_path.is_file():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip().lstrip("export ")] = v.strip().strip("'\"")

key = os.environ.get("FORMFAV_API_KEY")
url = "https://api.formfav.com/v1/form"
resp = httpx.get(url, params={"date": "2026-10-04", "track": "alice-springs", "race": 1, "race_code": "gallops", "country": "au", "timezone": "Australia/Darwin"}, headers={"X-API-Key": key})
print("Status:", resp.status_code)
import json
data = resp.json()
print("Keys:", list(data.keys()))
print("Sample:", json.dumps(data, indent=2)[:1000])
