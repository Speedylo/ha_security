# The August base experiments, re-run on `verify-2026-10-final` (2026-10-06)

The claim register's Tier C rows C01, C02 and CS16 rest on three experiments last run in August. Each
was re-run on the final tag's clone on the Pi, as its own README says to run it.

| Experiment | Compared with | Result |
|---|---|---|
| `host_isolation_probe/probe.sh` (`host_probe.txt`) | `results/pi5_memory_enabled.txt` | identical, apart from the date, the kernel's `max user namespaces` (15,850 → 15,866), and the shell's notice of the out-of-memory kill the probe causes on purpose |
| `cgroup_placement/place.py` (`placement.json`) | `results/pi5_placement.json` | every verdict identical; only the session and scope names differ. A first attempt ran it inside a user scope, which made its two positions the same one; it was re-run from the ssh session as its README says |
| `base_component/measure_base.py --count 6` (`base_component.json`) | `README.md`'s table | with the base component 160.4 MB at running (161.3) and PSS 136.0 MB (136.6); without it 109.0 and 89.5 MB; the base component's share 51.6 MB (51.9), its PSS difference 46.5 MB (46.6). All within ±5%. Capacity without the base component is 27 sandboxes, not 26, because PSS sits on a rounding boundary. Q4: `RestoreEntity` restores in both arms with the corrected recipe and not with §5.6.3's as published, as recorded |
