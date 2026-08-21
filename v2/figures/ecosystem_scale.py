#!/usr/bin/env python3
"""Measure the scale of the Home Assistant custom-integration ecosystem.

Every figure in report chapter 1 that carries a number comes from here, so the
chapter's claims can be regenerated and re-dated rather than trusted.

Source: `https://analytics.home-assistant.io/custom_integrations.json`, the
per-domain install counts published by Home Assistant's own opt-in telemetry.

    python3 ecosystem_scale.py [--refresh]

Writes `ecosystem_scale.json` next to this file: the derived figures plus the
retrieval date, so the chapter can cite a snapshot rather than a moving target.

**Stated limitation, carried into the chapter.** Analytics participation is
opt-in, so every count here is a *lower bound* on the true population. The bias
is also not neutral: users who enable telemetry are plausibly more engaged than
average, and more-engaged users are plausibly more likely to install third-party
extensions. The HACS penetration figure below should therefore be read as "at
least this, among installations that report", never as a population estimate.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import statistics
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "custom_integrations.json"
OUT = HERE / "ecosystem_scale.json"

SOURCE = "https://analytics.home-assistant.io/custom_integrations.json"

# Active installations reporting analytics, read from the dashboard at
# https://analytics.home-assistant.io/ on the date recorded below. The figure is
# rendered client-side, so it is transcribed rather than parsed.
ACTIVE_INSTALLATIONS = 669_743
ACTIVE_INSTALLATIONS_AS_OF = "2026-08-21"


def load(refresh: bool) -> dict:
    if refresh or not CACHE.exists():
        with urllib.request.urlopen(SOURCE, timeout=60) as response:
            CACHE.write_bytes(response.read())
    return json.loads(CACHE.read_text())


def derive(data: dict) -> dict:
    installs = {domain: entry.get("total", 0) for domain, entry in data.items()}
    counts = sorted(installs.values())
    total = sum(counts)
    hacs = installs.get("hacs", 0)

    top = sorted(installs.items(), key=lambda kv: kv[1], reverse=True)[:15]

    return {
        "source": SOURCE,
        "retrieved": dt.date.today().isoformat(),
        "active_installations": ACTIVE_INSTALLATIONS,
        "active_installations_as_of": ACTIVE_INSTALLATIONS_AS_OF,
        "distinct_custom_integrations": len(installs),
        "total_custom_integration_installs": total,
        "hacs_installs": hacs,
        # What fraction of reporting installations run the unvetted
        # distribution channel itself. The headline exposure figure.
        "hacs_share_of_installations": round(hacs / ACTIVE_INSTALLATIONS, 4),
        # Excluding HACS itself, so the figure counts extensions rather than
        # the store that delivers them.
        "mean_custom_integrations_per_installation": round(
            (total - hacs) / ACTIVE_INSTALLATIONS, 2
        ),
        "median_installs_per_integration": statistics.median(counts),
        "integrations_over_1000_installs": sum(1 for c in counts if c >= 1000),
        "integrations_over_10000_installs": sum(1 for c in counts if c >= 10_000),
        # The long tail matters for the argument: most custom integrations are
        # maintained for a very small audience, which is precisely the
        # population least likely to receive external review.
        "integrations_under_100_installs": sum(1 for c in counts if c < 100),
        "top_15": [{"domain": d, "installs": n} for d, n in top],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh", action="store_true", help="re-download instead of using the cache"
    )
    args = parser.parse_args()

    figures = derive(load(args.refresh))
    OUT.write_text(json.dumps(figures, indent=2) + "\n")

    print(f"source    : {figures['source']}")
    print(f"retrieved : {figures['retrieved']}\n")
    print(f"  active installations reporting     {figures['active_installations']:>10,}")
    print(f"  distinct custom integrations       {figures['distinct_custom_integrations']:>10,}")
    print(f"  total custom-integration installs  {figures['total_custom_integration_installs']:>10,}")
    print(f"  HACS installs                      {figures['hacs_installs']:>10,}")
    print(f"  HACS share of installations        {figures['hacs_share_of_installations']:>10.1%}")
    print(f"  mean custom integrations/install   {figures['mean_custom_integrations_per_installation']:>10.2f}")
    print(f"  median installs per integration    {figures['median_installs_per_integration']:>10,.0f}")
    print(f"  integrations >= 1,000 installs     {figures['integrations_over_1000_installs']:>10,}")
    print(f"  integrations >= 10,000 installs    {figures['integrations_over_10000_installs']:>10,}")
    print(f"  integrations < 100 installs        {figures['integrations_under_100_installs']:>10,}")
    print(f"\nwrote {OUT.name}")


if __name__ == "__main__":
    main()
