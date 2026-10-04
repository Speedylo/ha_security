"""Log in to Trakt once, with the device-code flow, and store the tokens for W2 (d).

Reads `~/.config/capstone/trakt.json`, which must already hold `client_id`, and `client_secret`
if Trakt issued one (mode 600). Trakt's app registration now issues PKCE public clients with no
secret (found 2026-10-04), so the secret is optional here; `trakt_tv` itself was written for the
older confidential clients, and whether it can refresh with a public one is what `--check-refresh`
tests. Asks Trakt for a device code and prints **only** the short user code and the address
to enter it at, then waits while you approve it in a browser. The tokens Trakt returns are written
back into the same file under `"token"`, in the shape Home Assistant's OAuth helper stores
(`access_token`, `refresh_token`, `expires_in`, `expires_at`, ...). No secret or token is ever
printed.

Device code rather than a redirect, because nothing here runs a web server for the redirect to
reach, and the flow is Trakt's documented one for devices without a browser.

Run on the Pi:  python3 trakt_device_login.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

FILE = Path.home() / ".config" / "capstone" / "trakt.json"
API = "https://api.trakt.tv"


def post(path: str, body: dict, client_id: str) -> tuple[int, dict]:
    request = urllib.request.Request(
        API + path, data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "trakt-api-version": "2",
                 "trakt-api-key": client_id, "User-Agent": "capstone-confine/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as err:
        return err.code, {}


def check_refresh(config: dict, client_id: str, client_secret: str) -> int:
    """One refresh, sent exactly as `trakt_tv`'s OAuth helper sends it; only the verdict is printed.

    Home Assistant's `LocalOAuth2Implementation._token_request` (pinned 2026.8.3,
    `helpers/config_entry_oauth2_flow.py`) posts **form-encoded** `grant_type=refresh_token`,
    `client_id` and `refresh_token`, and adds `client_secret` only if it is non-empty, so a public
    client sends none. No `redirect_uri`, no Trakt headers. If Trakt accepts it, the new tokens are
    stored, because Trakt's refresh tokens are single-use and the old one is now spent.
    """
    import urllib.parse

    token = config.get("token") or {}
    if not token.get("refresh_token"):
        print("no stored token yet: run without --check-refresh first")
        return 2
    form = {"grant_type": "refresh_token", "client_id": client_id,
            "refresh_token": token["refresh_token"]}
    if client_secret:
        form["client_secret"] = client_secret
    request = urllib.request.Request(
        API + "/oauth/token", data=urllib.parse.urlencode(form).encode(), method="POST",
        # The User-Agent Home Assistant's shared session sends (`helpers/aiohttp_client.py`,
        # SERVER_SOFTWARE). The first check sent Python's default and got 403, which is what
        # Cloudflare in front of Trakt gives clients it filters, not an OAuth refusal.
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": "HomeAssistant/2026.8.3 aiohttp/3.14.3 Python/3.14"})
    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            status, fresh = resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as err:
        status, fresh = err.code, {}
    if status != 200:
        print(f"  refresh refused: HTTP {status}")
        return 1
    fresh["expires_at"] = fresh.get("created_at", time.time()) + fresh["expires_in"]
    config["token"] = {**token, **fresh}
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(config, indent=2))
    os.chmod(tmp, 0o600)
    tmp.replace(FILE)
    rotated = fresh.get("refresh_token") not in (None, token["refresh_token"])
    print(f"  refresh accepted {'without' if not client_secret else 'with'} a client_secret; "
          f"refresh token {'rotated' if rotated else 'unchanged'}; new tokens stored")
    return 0


def main() -> int:
    if not FILE.exists():
        print(f"{FILE} does not exist: create it with client_id and client_secret first")
        return 2
    if FILE.stat().st_mode & 0o077:
        print(f"{FILE} is readable by others; run: chmod 600 {FILE}")
        return 2
    config = json.loads(FILE.read_text())
    client_id, client_secret = config.get("client_id"), config.get("client_secret")
    if not client_id:
        print(f"{FILE} needs client_id")
        return 2
    if "--check-refresh" in sys.argv:
        return check_refresh(config, client_id, client_secret or "")

    status, code = post("/oauth/device/code", {"client_id": client_id}, client_id)
    if status != 200:
        print(f"Trakt refused the device-code request (HTTP {status}); check the client_id")
        return 1
    print(f"\n  Go to {code['verification_url']} and enter:  {code['user_code']}\n")
    print(f"  (waiting up to {code['expires_in'] // 60} minutes)")

    deadline = time.monotonic() + code["expires_in"]
    while time.monotonic() < deadline:
        time.sleep(code.get("interval", 5))
        body = {"code": code["device_code"], "client_id": client_id}
        if client_secret:
            body["client_secret"] = client_secret
        status, token = post("/oauth/device/token", body, client_id)
        if status == 200:
            token["expires_at"] = token.get("created_at", time.time()) + token["expires_in"]
            config["token"] = token
            tmp = FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(config, indent=2))
            os.chmod(tmp, 0o600)
            tmp.replace(FILE)
            expires = time.strftime("%Y-%m-%d %H:%M", time.localtime(token["expires_at"]))
            print(f"\n  approved; tokens stored in {FILE} (access token expires {expires})")
            return 0
        if status == 400:            # pending: not approved yet
            continue
        if status == 429:            # polling too fast
            time.sleep(5)
            continue
        messages = {404: "invalid device code", 409: "code already used",
                    410: "code expired", 418: "you denied the request"}
        print(f"\n  stopped: {messages.get(status, f'HTTP {status}')}")
        return 1
    print("\n  stopped: the code expired before it was approved")
    return 1


if __name__ == "__main__":
    sys.exit(main())
