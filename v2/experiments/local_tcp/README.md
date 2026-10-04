# Experiment — a real integration reaching a home-network device, confined (W2 (a))

**Run:** 2026-10-04 · **Target:** Pi 5 · **Feeds:** §7.40 · **Predictions:** `notes/w2a_local_tcp_prediction.md`

`midea_ac_lan` 2026.8.0 with `midea-lan` 2026.8.0, unmodified, against `fake_midea.py` on the Pi's
LAN address (10.126.83.113): a protocol-V2 air conditioner that answers discovery on UDP 6445/20086,
accepts TCP 6444, and logs every datagram and connection with its source address.

    systemd-run --user --scope -q python3 -u -m confine.endtoend_local --corpus ~/r2exp/corpus \
        --python ~/r2exp/ha314/bin/python --json out.json

| `results/w2a_20261004/` | |
|---|---|
| `final_ABC.json`, `.log` | the result: all three arms on the built code, every report present |
| `build_ABC.json`, `.log` | the same before the print-before-shutdown fix; arm A's report lost to shutdown |
| `prebuild_B_stuck_summary.json` | baseline arm B: hung in discovery, 1,471 polls in 25 min |
| `prebuild_B_device.jsonl` | what the device saw in baseline arm B: two discovery datagrams |
| `prebuild_C_flood_summary.json` | baseline arm C: 463,631 refused decisions in 7.5 min (the 289 MB log itself deleted) |

| Arm | Loaded | Device saw | Decisions |
|---|---|---|---|
| A unconfined | yes | 2 datagrams, 8 connections, 7,616 bytes | — |
| B confined, `network.local` declared | **yes** | 2 datagrams, 6 connections, 4,440 bytes, all from the host | 2 send, 8 recv, 6 tcp.local, all allowed |
| C confined, nothing declared | no (`invalid_device_ip`) | **nothing** | 9 sends refused |
