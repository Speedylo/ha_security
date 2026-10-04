# Experiment — an OAuth token refreshed inside a sandbox (W2 (d))

**Run:** 2026-10-04 · **Target:** Pi 5 · **Feeds:** §7.42 · **Predictions:** `notes/w2d_token_refresh_prediction.md`

`trakt_tv` 0.17.0, unmodified, with Younes's own free Trakt account (a public PKCE client: Trakt no
longer issues secrets). Credentials in `~/.config/capstone/trakt.json` on the Pi, mode 600; logged
in once with `trakt_device_login.py` (device code; prints only the user code). Nothing here contains
a token or the client id: `endtoend_oauth` scrubs every report, and the files were scanned against
the live credentials before commit.

    systemd-run --user --scope -q python3 -u -m confine.endtoend_oauth \
        --corpus ~/r2exp/corpus_uniform --python ~/r2exp/ha314/bin/python --json out.json

| `results/w2d_20261004/` | |
|---|---|
| `runs.json`, `.log` | **the result**: four runs, TMDB declared |
| `runs_tmdb_undeclared.*` | the same, `api.tmdb.org:80` undeclared: refused 6×, setup never finished |
| `runs_stats_source.*` | the first source, the user's stats: Trakt answers 204 with no body for an empty account |
| `nordpool.*`, `localtuya.*` | regression runs after fixing the W2 (b) regression this work found |

| Run | Loaded | Token | |
|---|---|---|---|
| 1 expiring | **yes** | refreshed inside the sandbox; new pair only in (B)'s storage | a token expiring while it runs |
| 2 respawn, spent token | no: **400**, "could not authenticate" | — | a respawn without the data directory |
| 3 respawn, (B)'s token | **yes** | refreshed again | a respawn with it |
| C nothing declared | no | untouched; egress refused | the control |
