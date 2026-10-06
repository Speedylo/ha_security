# Durability and the memory bound's cost — §7.20

*Written 2026-10-06 (verification finding F07): until then this directory had no README.*

`measure.py` answers two Phase C obligations that share a harness (its docstring gives the
reasoning in full):

- **What an `fsync` per decision costs** (§6.8.3). §5.11.3 writes the audit record before the
  action, and that ordering is worth nothing unless the record is durable first. `audit.py` already
  pays for an `fsync` on every decision, and this measures what it pays.
- **What `resources.memory_mb` costs a legitimate integration** (§6.9.4, §7.6's P5). cgroup v2
  charges page cache to the cgroup that read the file, so a memory bound also bounds reading a large
  file.

Both measurements were invalid on their first run. They wrote to `/tmp`, which is RAM on the Pi, so
the `fsync` cost nothing and the "file" was memory. §7.20 records this before giving either number.

| File | What it is | Cited by |
|---|---|---|
| `results/pi5.json` | the measurement, run 2026-09-02 on the Pi, on disk rather than `/tmp` | §7.20 |
| `results/t4_20261003/` | the logs of T4's run on 2026-10-03: every suite, the compatibility arm and two end-to-end runs, after the durable audit log was wired into every harness | §7.32 (T4) |

```bash
systemd-run --user --scope -q python3 measure.py --json results/pi5.json
```
