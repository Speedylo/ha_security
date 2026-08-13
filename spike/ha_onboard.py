#!/usr/bin/env python3
"""Onboard a fresh Home Assistant headlessly and mint a long-lived token.

A stock HA insists on a browser wizard before it will issue credentials, which
would make "run the framework against real HA" a manual step and therefore not
reproducible. HA does expose the same wizard as a REST API, so this drives it:

    create the owner account   POST /api/onboarding/users      -> auth code
    exchange for a session     POST /auth/token                -> access token
    finish the remaining steps POST /api/onboarding/*
    mint a durable credential  WebSocket auth/long_lived_access_token

The token is written to .ha_token (git-ignored) for run_targets.sh to pick up.
Only the supervisor ever reads it; the sandboxed integration has no route to it.

    ./ha_onboard.py                      # onboard, or reuse an existing token
    ./ha_onboard.py --force              # mint a new token even if one exists
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOKEN_FILE = HERE / ".ha_token"

CLIENT_ID = "http://127.0.0.1:8123/"
DEFAULT_URL = "http://127.0.0.1:8123"
OWNER = {"name": "Capstone", "username": "capstone", "password": "capstone-spike-password"}


def post(url: str, payload: dict, token: str | None = None) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw) if raw.strip() else {}


def post_form(url: str, fields: dict) -> dict:
    body = urllib.parse.urlencode(fields).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST")
    request.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(request, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def token_works(base_url: str, token: str) -> bool:
    request = urllib.request.Request(f"{base_url}/api/config")
    request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=10) as resp:
            return resp.status == 200
    except Exception:  # noqa: BLE001 - any failure means "mint a new one"
        return False


def onboard(base_url: str) -> str:
    """Create the owner account and return a short-lived access token."""
    try:
        result = post(
            f"{base_url}/api/onboarding/users",
            {"client_id": CLIENT_ID, "language": "en", **OWNER},
        )
    except urllib.error.HTTPError as err:
        if err.code == 403:
            raise SystemExit(
                "This Home Assistant has already been onboarded, and its owner password is\n"
                "not recoverable. Either pass an existing long-lived token via --token, or\n"
                "wipe the instance and start over:\n"
                "    ./ha_docker.sh down && rm -rf .ha_config && ./ha_docker.sh up"
            ) from err
        raise

    code = result["auth_code"]
    tokens = post_form(
        f"{base_url}/auth/token",
        {"grant_type": "authorization_code", "code": code, "client_id": CLIENT_ID},
    )
    return tokens["access_token"]


def finish_onboarding(base_url: str, token: str) -> None:
    """Complete the remaining wizard steps so HA reaches a normal running state."""
    for step, payload in (
        ("core_config", {}),
        ("analytics", {}),
        ("integration", {"client_id": CLIENT_ID, "redirect_uri": CLIENT_ID}),
    ):
        try:
            post(f"{base_url}/api/onboarding/{step}", payload, token=token)
        except urllib.error.HTTPError as err:
            # Steps already completed answer 403; that is success, not failure.
            if err.code not in (403, 404):
                print(f"  onboarding step {step}: HTTP {err.code}", file=sys.stderr)


async def _mint(base_url: str, access_token: str) -> str:
    """Long-lived tokens are only issuable over the WebSocket API, not REST."""
    import aiohttp

    ws_url = base_url.replace("https://", "wss://").replace("http://", "ws://") + "/api/websocket"
    async with aiohttp.ClientSession() as session, session.ws_connect(ws_url) as ws:
        hello = json.loads(await ws.receive_str())
        if hello.get("type") != "auth_required":
            raise SystemExit(f"unexpected greeting from HA: {hello}")

        await ws.send_str(json.dumps({"type": "auth", "access_token": access_token}))
        if json.loads(await ws.receive_str()).get("type") != "auth_ok":
            raise SystemExit("HA rejected the access token during WebSocket auth")

        await ws.send_str(
            json.dumps(
                {
                    "id": 1,
                    "type": "auth/long_lived_access_token",
                    "client_name": "capstone-supervisor",
                    "lifespan": 3650,
                }
            )
        )
        reply = json.loads(await ws.receive_str())

    if not reply.get("success"):
        raise SystemExit(f"could not mint a long-lived token: {reply}")
    return reply["result"]


def mint_long_lived(base_url: str, access_token: str) -> str:
    return asyncio.run(_mint(base_url, access_token))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--force", action="store_true", help="mint a new token even if one works")
    parser.add_argument("--token", help="use this existing long-lived token instead of onboarding")
    args = parser.parse_args()

    if args.token:
        if not token_works(args.url, args.token):
            print("that token does not work against this instance", file=sys.stderr)
            return 1
        TOKEN_FILE.write_text(args.token, encoding="utf-8")
        print(f"token accepted and written to {TOKEN_FILE.name}")
        return 0

    if not args.force and TOKEN_FILE.exists():
        existing = TOKEN_FILE.read_text(encoding="utf-8").strip()
        if existing and token_works(args.url, existing):
            print(f"existing token in {TOKEN_FILE.name} still works")
            return 0

    print(f"onboarding {args.url} ...")
    access_token = onboard(args.url)
    finish_onboarding(args.url, access_token)
    token = mint_long_lived(args.url, access_token)
    TOKEN_FILE.write_text(token, encoding="utf-8")
    TOKEN_FILE.chmod(0o600)
    print(f"long-lived token written to {TOKEN_FILE.name} (mode 600)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
