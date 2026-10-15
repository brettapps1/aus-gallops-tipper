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
print("API Key loaded:", bool(key), repr(key[:5] if key else None))

url = "https://api.formfav.com/v1/form/meetings"
resp = httpx.get(url, params={"date": "2026-10-04", "race_code": "gallops"}, headers={"X-API-Key": key})
print("Status:", resp.status_code)
print("Body:", resp.text[:1000])
