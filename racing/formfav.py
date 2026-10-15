#!/usr/bin/env python3
"""
FormFav CLI — horse racing data from your terminal.

Covers meetings, race form, predictions, and jockey stats (+ trainer,
track-bias, runner search/profile, venues).

Usage:
    export FORMFAV_API_KEY=your_api_key   # or put it in .env
    python formfav.py meetings 2026-04-03
    python formfav.py race-card 2026-04-03 flemington 5
    python formfav.py predictions 2026-04-03 randwick 3
    python formfav.py jockey-stats "J McDonald"
    python formfav.py venues --country au

Output is JSON by default (pipe-friendly).
Get an API key at https://formfav.com/pricing
Spec: https://api.formfav.com/v1/openapi.json
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

import httpx
import typer

app = typer.Typer(
    name="formfav",
    help="Horse racing data — form, predictions, and statistics.",
    no_args_is_help=True,
)


def _load_dotenv() -> None:
    """Minimal .env loader (no extra dep). Checks cwd then home then FORMFAV_DOTENV."""
    candidates = []
    if os.environ.get("FORMFAV_DOTENV"):
        candidates.append(Path(os.environ["FORMFAV_DOTENV"]))
    candidates += [Path.cwd() / ".env", Path.home() / ".env"]
    seen = set()
    for p in candidates:
        if str(p) in seen:
            continue
        seen.add(str(p))
        if not p.is_file():
            continue
        try:
            for line in p.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip().lstrip("export ")
                v = v.strip().strip("'\"")
                if k and k not in os.environ:
                    os.environ[k] = v
        except Exception:
            continue


_load_dotenv()

API_BASE = os.environ.get("FORMFAV_API_URL", "https://api.formfav.com/v1").rstrip("/")


def _api_key() -> str:
    return os.environ.get("FORMFAV_API_KEY", "").strip().strip("'\"")


def _request(method: str, path: str, **kwargs) -> dict | list:
    key = _api_key()
    if not key:
        typer.echo(
            "Error: FORMFAV_API_KEY not set. Put it in .env or export it. "
            "Get a key at https://formfav.com/pricing",
            err=True,
        )
        raise typer.Exit(1)

    try:
        with httpx.Client(
            base_url=API_BASE,
            headers={"X-API-Key": key},
            timeout=30.0,
        ) as client:
            resp = client.request(method, path, **kwargs)
    except httpx.ConnectError:
        typer.echo(f"Error: Cannot connect to FormFav API at {API_BASE}", err=True)
        raise typer.Exit(1)
    except httpx.TimeoutException:
        typer.echo("Error: Request timed out.", err=True)
        raise typer.Exit(1)

    if resp.status_code == 200:
        try:
            return resp.json()
        except Exception:
            typer.echo(f"Error: Non-JSON 200 response: {resp.text[:500]}", err=True)
            raise typer.Exit(1)

    try:
        detail = resp.json().get("detail", resp.text)
    except Exception:
        detail = resp.text

    messages = {
        401: "Invalid or missing API key. Check FORMFAV_API_KEY.",
        403: f"Pro subscription required. {detail}",
        404: f"Not found: {detail}",
        400: f"Bad request: {detail}",
        422: f"Validation error: {detail}",
        429: "Rate limit exceeded. Wait before making more requests.",
    }
    typer.echo(
        f"Error: {messages.get(resp.status_code, f'API error ({resp.status_code}): {detail}')}",
        err=True,
    )
    # Hint for free-tier Pro endpoints
    if resp.status_code == 403:
        typer.echo(
            "Hint: /predictions and /stats/* need Pro. "
            "Use 'meetings' / 'race-card' on free tier, or heuristic fallback "
            "(see fair-dinkum-publishing-agent-workflowz/app/services/formfav.py).",
            err=True,
        )
    raise typer.Exit(1)


def _output(data: dict | list, out: Optional[str] = None):
    text = json.dumps(data, indent=2)
    if out:
        Path(out).write_text(text)
        typer.echo(f"Saved to {out}", err=True)
    else:
        typer.echo(text)


def _opt_out() -> Optional[str]:
    return typer.Option(None, "--out", "-o", help="Save JSON to file instead of stdout")


@app.command()
def meetings(
    date: str = typer.Argument(help="Race date (YYYY-MM-DD, within ±7 days)"),
    race_code: str = typer.Option("gallops", help="gallops, harness, or greyhounds"),
    timezone: Optional[str] = typer.Option(None, help="IANA tz, e.g. Australia/Sydney"),
    out: Optional[str] = _opt_out(),
):
    """List race meetings for a date (free tier)."""
    params: dict = {"date": date, "race_code": race_code}
    if timezone:
        params["timezone"] = timezone
    _output(_request("GET", "/form/meetings", params=params), out)


@app.command("race-card")
def race_card(
    date: str = typer.Argument(help="Race date (YYYY-MM-DD)"),
    track: str = typer.Argument(help="Track slug (e.g. flemington). See 'venues'."),
    race: int = typer.Argument(help="Race number 1-20"),
    race_code: str = typer.Option("gallops", help="gallops, harness, or greyhounds"),
    country: str = typer.Option("au", help="Country code, e.g. au, nz, hk, gb, us, jp, sg, fr, ie"),
    timezone: Optional[str] = typer.Option(None, help="IANA tz scope"),
    out: Optional[str] = _opt_out(),
):
    """Get the full race form for a race (free tier)."""
    params = {
        "date": date, "track": track, "race": race,
        "race_code": race_code, "country": country,
    }
    if timezone:
        params["timezone"] = timezone
    _output(_request("GET", "/form", params=params), out)


@app.command()
def predictions(
    date: str = typer.Argument(help="Race date (YYYY-MM-DD)"),
    track: str = typer.Argument(help="Track slug"),
    race: int = typer.Argument(help="Race number 1-20"),
    race_code: str = typer.Option("gallops", help="gallops, harness, or greyhounds"),
    country: str = typer.Option("au", help="Country code"),
    timezone: Optional[str] = typer.Option(None, help="IANA tz scope"),
    out: Optional[str] = _opt_out(),
):
    """Get ML win/place probability predictions (Pro tier)."""
    params = {
        "date": date, "track": track, "race": race,
        "race_code": race_code, "country": country,
    }
    if timezone:
        params["timezone"] = timezone
    _output(_request("GET", "/predictions", params=params), out)


@app.command("jockey-stats")
def jockey_stats(
    name: str = typer.Argument(help="Jockey name (partial match OK)"),
    race_code: str = typer.Option("gallops", help="gallops or harness"),
    window: Optional[int] = typer.Option(None, help="Rolling window in days (14-365)"),
    out: Optional[str] = _opt_out(),
):
    """Get jockey performance stats by track (Pro tier)."""
    params: dict = {"race_code": race_code}
    if window is not None:
        params["window"] = window
    _output(_request("GET", f"/stats/jockey/{name}", params=params), out)


@app.command("trainer-stats")
def trainer_stats(
    name: str = typer.Argument(help="Trainer name (partial match OK)"),
    race_code: str = typer.Option("gallops", help="gallops, harness, or greyhounds"),
    window: Optional[int] = typer.Option(None, help="Rolling window in days (14-365)"),
    out: Optional[str] = _opt_out(),
):
    """Get trainer performance stats by track (Pro tier)."""
    params: dict = {"race_code": race_code}
    if window is not None:
        params["window"] = window
    _output(_request("GET", f"/stats/trainer/{name}", params=params), out)


@app.command("track-bias")
def track_bias(
    track: str = typer.Argument(help="Track slug (e.g. flemington)"),
    race_code: str = typer.Option("gallops", help="gallops, harness, or greyhounds"),
    country: str = typer.Option("au", help="Country code, e.g. au, nz, hk, gb, us, jp, sg, fr, ie"),
    window: Optional[int] = typer.Option(None, help="Rolling window in days (14-365)"),
    condition: Optional[str] = typer.Option(None, help="Track condition: Good, Soft, Heavy"),
    distance: Optional[str] = typer.Option(None, help="Metres: 1200 or a range 1200-1600"),
    out: Optional[str] = _opt_out(),
):
    """Get barrier/box bias for a venue (Pro tier)."""
    params: dict = {"race_code": race_code, "country": country}
    if window is not None:
        params["window"] = window
    if condition is not None:
        params["condition"] = condition
    if distance is not None:
        params["distance"] = distance
    _output(_request("GET", f"/stats/track-bias/{track}", params=params), out)


@app.command("search-runner")
def search_runner(
    query: str = typer.Argument(help="Runner name (min 3 characters)"),
    race_code: str = typer.Option("gallops", help="gallops, harness, or greyhounds"),
    country: Optional[str] = typer.Option(None, help="Country filter, e.g. au, nz, hk, gb, us, jp, sg, fr, ie"),
    out: Optional[str] = _opt_out(),
):
    """Search for a horse or greyhound by name (Pro tier)."""
    params: dict = {"q": query, "race_code": race_code}
    if country is not None:
        params["country"] = country
    _output(_request("GET", "/stats/runner/search", params=params), out)


@app.command("runner-profile")
def runner_profile(
    runner_id: int = typer.Argument(help="Runner ID (from search-runner)"),
    window: Optional[int] = typer.Option(None, help="Rolling window in days (14-365)"),
    out: Optional[str] = _opt_out(),
):
    """Get full career statistics for a runner (Pro tier)."""
    params: dict = {}
    if window is not None:
        params["window"] = window
    _output(_request("GET", f"/stats/runner/{runner_id}", params=params), out)


@app.command()
def venues(
    race_type: Optional[str] = typer.Option(None, "--race-type", help="gallops, harness, or greyhounds"),
    country: Optional[str] = typer.Option(None, help="Country filter, e.g. au"),
    out: Optional[str] = _opt_out(),
):
    """List known track slugs (free tier) — use to find 'track' values."""
    params: dict = {}
    if race_type:
        params["raceType"] = race_type
    if country:
        params["country"] = country
    _output(_request("GET", "/form/venues", params=params), out)


if __name__ == "__main__":
    app()
