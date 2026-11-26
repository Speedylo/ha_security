# Helper-layer share: community vs built-in integrations (2026-11-26)

Why: Table 9.1 justified "a real Home Assistant runtime, not a stand-in" with 91% of the 1,482
integrations *shipped* with Home Assistant (24 Aug grep). The framework confines *community*
integrations, and the 24 Aug community figure (100%) was never in a pinned run (the 16 Oct and
1 Nov step 12 runs measured `hass` handles only). Younes asked whether the reason was the right one.

Run on the Pi 5 (aarch64), Python 3.14.7 from `~/r2exp/ha314`, script `experiments/verify/helper_layer.py`
(repo at dfe3ec3; the script is new and was run before it was committed).

| Corpus | Where | n | Text `homeassistant.helpers` | Real import (ast) | Unparseable |
|---|---|---|---|---|---|
| hacs-top150 | `~/r2exp/final2-run/top150` (fetched 1 Nov from `figures/hacs_top150_manifest.json`) | 144 | 144 (100.0%) | 144 (100.0%) | 0 |
| core-2026.8.3 | `homeassistant/components` in the venv, HA 2026.8.3 | 1,482 | 1,356 (91.5%) | 1,356 (91.5%) | 0 |

Corpus check: the same 144 domains as the manifest; 4,628 `.py` files, equal per integration to
`final_20261016` and `final2_20261101` step 12 (`files` field). The manifest's `py_files` counts
the whole repository, so four integrations differ there (chime_tts, dwains_dashboard,
solaredge_modbus_multi, f1_sensor); not a corpus difference.

The core row reproduces the 24 Aug count exactly (1,356/1,482). Files: `hacs_top150.json`, `core.json`.
