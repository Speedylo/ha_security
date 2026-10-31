"""What (A)'s own UI does with what a confined integration publishes (bridge batch B5, 2026-10-31).

`notes/bridge_kinds_b5_prediction_20261031.md`. Every other suite reads (A) through its API; this one
opens (A)'s UI in a browser, as the household does, because what the frontend does with a published
string or link is not visible in the state. A confined integration publishes markup in a state, a
name and an attribute, and picture links (F71). Chromium, headless on the Pi, is driven through its
DevTools protocol over the framework's own WebSocket client (`ws.py`), logged in to (A) with the
household's token: the overview's devices page, an entity's dialog and its details, and the entity
list in the settings. (A) loads no history or logbook (`house_a.py`'s configuration has no recorder),
so those two pages are not checked; adding them would change (A) for every other run.

Every payload points at a **marker server** this suite runs on the loopback: a tag the browser
interprets as HTML requests `/html/…`, script that runs requests `/ran/…`, a picture the browser
loads requests `/picture/…`. So "nothing ran" is read from requests the browser made, not from the
page, in any frame or shadow root.

    D0  control: the same payload, put into the page as HTML on purpose, is seen (`/html`, `/ran`)
    D1  on each page, the published name is drawn (so a page that drew nothing cannot pass)
    D2  the state and the name appear as text, markup included, in the entity's dialog, and the
        attributes in its details
    D3  on no page is any markup interpreted or any script run (no `/html/`, no `/ran/` request)
    D4  no page loads a picture link the integration published (F71: no `/picture/` request)

Out of scope, stated: cards a user configures themselves (a markdown card renders markdown), and
links the user must click (a `javascript:` link is published and must show as text; it is not
clicked).

Requires (A) running and `chromium` on the PATH. `--out DIR` keeps a screenshot of every page.

Run:  python3 -m confine.selftest_display [--out DIR]
"""

from __future__ import annotations

import argparse
import base64
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import house_a
from .audit import AuditLog
from .mediator import Mediator
from .platform import ActingPolicy
from .real_platform import RealPlatform
from .selftest_push import Sandbox
from .selftest_real_platform import check, manifest, results
from .ws import WebSocket

NAME = "Hostile name"

# Every text node of the page, through every shadow root: what a person can read.
TEXT = """(() => { const out = [];
  const walk = n => { if (n.nodeType === 3) out.push(n.textContent);
    if (n.shadowRoot) walk(n.shadowRoot); for (const c of n.childNodes) walk(c); };
  walk(document); return out.join(' '); })()"""

# Opens the dialog's details (its menu's "Details" item), where the attributes are shown.
DETAILS = """(() => { let n = 0;
  const walk = e => { if (e.tagName === 'HA-DROPDOWN-ITEM' && e.textContent.trim() === 'Details') {
      e.click(); n++; }
    if (e.shadowRoot) walk(e.shadowRoot); for (const c of e.children || []) walk(c); };
  walk(document.documentElement); return n; })()"""


class Marker:
    """A loopback HTTP server that records the path of every request the browser makes to it."""

    def __init__(self) -> None:
        seen = self.seen = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                seen.append(self.path)
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

            def log_message(self, *args) -> None:
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def hits(self, prefix: str) -> list[str]:
        return [p for p in self.seen if p.startswith(prefix)]

    def close(self) -> None:
        self.server.shutdown()


class Browser:
    """Headless Chromium, one page, driven over the DevTools protocol."""

    def __init__(self, profile: Path) -> None:
        self.process = subprocess.Popen(
            [shutil.which("chromium") or "chromium", "--headless=new", "--disable-gpu",
             "--no-first-run", "--no-default-browser-check", f"--user-data-dir={profile}",
             # Without a desktop session, Chromium otherwise waits for a keyring and loads no page.
             "--password-store=basic",
             "--remote-debugging-port=0", "--window-size=1280,1600", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        port_file = profile / "DevToolsActivePort"
        for _ in range(100):
            if port_file.exists() and port_file.read_text().strip():
                break
            time.sleep(0.1)
        port = int(port_file.read_text().split()[0])
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=10) as answer:
            page = next(t for t in json.load(answer) if t.get("type") == "page")
        path = page["webSocketDebuggerUrl"].split(f":{port}", 1)[1]
        self.ws = WebSocket("127.0.0.1", port, path, timeout=60)
        self._next = 0

    def call(self, method: str, **params) -> dict:
        self._next += 1
        ident = self._next
        self.ws.send({"id": ident, "method": method, "params": params})
        while True:
            for message in self.ws.receive():
                if message.get("id") == ident:
                    if "error" in message:
                        raise RuntimeError(f"{method}: {message['error']}")
                    return message.get("result") or {}

    def evaluate(self, expression: str):
        answer = self.call("Runtime.evaluate", expression=expression, returnByValue=True,
                           awaitPromise=True)
        return (answer.get("result") or {}).get("value")

    def go(self, url: str) -> None:
        self.call("Page.navigate", url=url)
        time.sleep(1)

    def text_once(self, wanted: str, seconds: float = 30) -> str:
        """The page's text once it contains `wanted`, or whatever it holds when time runs out."""
        deadline = time.monotonic() + seconds
        text = ""
        while time.monotonic() < deadline:
            text = self.evaluate(TEXT) or ""
            if wanted in text:
                return text
            time.sleep(0.5)
        return text

    def screenshot(self, path: Path | None) -> None:
        if path is not None:
            data = self.call("Page.captureScreenshot", format="png").get("data", "")
            path.write_bytes(base64.b64decode(data))

    def close(self) -> None:
        try:
            self.ws.close()
        finally:
            self.process.terminate()
            self.process.wait(timeout=10)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, help="a directory for a screenshot of every page")
    args = ap.parse_args()
    if not house_a.running():
        print("(A) is not running: python3 -m confine.house_a up --fresh")
        return 2
    if shutil.which("chromium") is None:
        print("chromium is not on the PATH")
        return 2
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)

    marker = Marker()
    m = marker.base
    DEVICES = f"{house_a.BASE}/home/other-devices"  # the overview's page for devices in no area
    HOSTILE = "sensor.selftest_hostile"
    PICTURED = "switch.selftest_pictured"
    name = f'{NAME} <img src="{m}/html/name" onerror="fetch(\'{m}/ran/name\')">'
    states = (f'<img src="{m}/html/state" onerror="fetch(\'{m}/ran/state\')">',
              f"<script>fetch('{m}/ran/state2')</script>")
    attributes = {"friendly_name": name,
                  "note": f'<b>bold</b><img src="{m}/html/attr" onerror="fetch(\'{m}/ran/attr\')">',
                  "link": f"javascript:fetch('{m}/ran/link')",
                  "entity_picture": f"{m}/picture/sensor?data=read-by-the-integration"}

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        platform = RealPlatform()
        log = AuditLog(path=root / "audit" / "decisions.jsonl")
        mediator = Mediator(policy=ActingPolicy({}, platform), log=log)
        mediator.attach_platform(platform)
        sandbox = Sandbox(mediator, "selftest", manifest(root, "selftest", {}))

        for state in states:
            published = sandbox.ask({"op": "entity.publish", "entity": HOSTILE, "state": state,
                                     "attributes": attributes})
        sandbox.ask({"op": "entity.publish", "entity": HOSTILE, "state": states[0],
                     "attributes": attributes})
        pictured = sandbox.ask({"op": "entity.publish", "entity": PICTURED, "state": "on",
                                "attributes": {"friendly_name": f"{NAME} switch",
                                               "entity_picture_local": f"{m}/picture/switch"}})
        hostile = platform.published.get(("selftest", HOSTILE)) or HOSTILE
        switch = platform.published.get(("selftest", PICTURED)) or PICTURED
        print(f"\npublished: {hostile} {published.get('ok')}, {switch} {pictured.get('ok')}\n")

        browser = Browser(root / "chrome")
        try:
            # Logged in as the household: the frontend reads its tokens from local storage.
            browser.go(f"{house_a.BASE}/")
            tokens = {"access_token": house_a.TOKEN_FILE.read_text().strip(),
                      "token_type": "Bearer", "expires_in": 1800, "hassUrl": house_a.BASE,
                      "clientId": f"{house_a.BASE}/", "refresh_token": "",
                      "expires": int(time.time() * 1000) + 10 * 365 * 86400 * 1000}
            browser.evaluate(f"localStorage.setItem('hassTokens', {json.dumps(json.dumps(tokens))})")

            print("D0 — control: the detector sees a payload that is interpreted\n")
            browser.go(DEVICES)
            browser.text_once(NAME, seconds=20)
            browser.evaluate("document.body.insertAdjacentHTML('beforeend', "
                             + json.dumps(f'<img src="{m}/html/control" '
                                          f'onerror="fetch(\'{m}/ran/control\')">') + ")")
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and not marker.hits("/ran/control"):
                time.sleep(0.2)
            check("D0 markup put into the page on purpose is seen: the tag and its script",
                  bool(marker.hits("/html/control")) and bool(marker.hits("/ran/control")),
                  f"{marker.seen}")
            marker.seen.clear()

            def page(label: str, url: str | None, more_info: str | None = None,
                     details: bool = False) -> str:
                if url is not None:
                    browser.go(url)
                if more_info is not None:
                    browser.text_once(NAME, seconds=20)
                    browser.evaluate(
                        "document.querySelector('home-assistant').dispatchEvent(new CustomEvent("
                        f"'hass-more-info', {{detail: {{entityId: {json.dumps(more_info)}}}, "
                        "bubbles: true, composed: true}))")
                    time.sleep(2)
                    if details:
                        check(f"{label}: the dialog's Details item is found",
                              browser.evaluate(DETAILS) == 1)
                        time.sleep(2)
                text = browser.text_once(NAME)
                time.sleep(3)  # pictures and tags requested by what was just drawn
                browser.screenshot(args.out / f"{label}.png" if args.out else None)
                check(f"D1 {label}: the published name is drawn", NAME in text,
                      text[:120].replace("\n", " "))
                return text

            print("\nD1–D4 — each page\n")
            pages = {}
            pages["devices"] = page("devices", DEVICES)
            pages["dialog"] = page("dialog", None, more_info=hostile)
            pages["details"] = page("details", DEVICES, more_info=hostile, details=True)
            pages["switch_dialog"] = page("switch_dialog", DEVICES, more_info=switch)
            pages["entities"] = page("entities", f"{house_a.BASE}/config/entities")

            print("\nD2 — what was published appears as text\n")
            dialog, details = pages["dialog"], pages["details"]
            check("D2 the dialog shows the state as text, markup included", states[0] in dialog,
                  "" if states[0] in dialog else dialog[:200])
            check("D2 the dialog shows the name as text, markup included", name in dialog)
            check("D2 the details show the attributes as text, markup and link included",
                  attributes["note"] in details and attributes["link"] in details,
                  details[details.find("note") - 20:][:200] if "note" in details else "")

            print("\nD3, D4 — what the browser requested\n")
            check("D3 no page interpreted a published tag (no /html/ request)",
                  not marker.hits("/html/"), f"{marker.hits('/html/')}")
            check("D3 no page ran a published script (no /ran/ request)",
                  not marker.hits("/ran/"), f"{marker.hits('/ran/')}")
            check("D4 no page loaded a picture link the integration published (F71)",
                  not marker.hits("/picture/"), f"{marker.hits('/picture/')}")
        finally:
            browser.close()
            marker.close()
            platform.close()
        check("every chain verifies", log.verify() == [])

    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
