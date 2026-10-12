# §10 Feasibility — plan and decisions (2026-10-12)

Budget 700 words, 2 pp; drafted at about 850 (trim at week 6 or on review). Skill loaded before drafting.
Rebuilt from the working report, not the 2026-09-08 draft, whose figures were stale (31.5 µs, 120 MB,
26-sandbox budget from the old footprint, "push loop missing", "mediator on a stand-in").

**Sources checked:** host probe `report/05_architecture.md` §5.7 table (seven namespace types, seccomp with
`user_notif`, `memory` missing by `cgroup_disable=memory`), `namespaces.py` (the seven the framework uses;
kernel 6.12 has eight with `time`, so "all seven the design uses"); `io` not delegated [48]; entry-point
problem `report/06_implementation.md:109`; memory figures as Table 12.4 (56.5 / 135.6 MB PSS, 17–43
sandboxes); supervisor and mediator stdlib only (`ctypes` included; `aiohttp`/`homeassistant` only in
`sandbox_runtime.py`); live services from Table 12.3 (nordpool, smhi_brandrisk, regensburg_transport,
dwd_weather public; pirateweather free key, trakt_tv free account; midea_ac_lan, localtuya simulated);
only `sudo` step in `REPRODUCE.md` is the boot change; RFC [11] framing from `report/01` §1.9.

**Dropped from the old draft:** the clone3/cgroup-placement paragraph (§9 covers delegation), the
26-of-37 credential point (§11 has it), "market need" (§2 has it), the "at your own risk" quote (unsourced).

**For Younes:** the four PDFs in `refs/` are tracked and pushed (private repo). The old draft said they
"are not redistributed"; that holds only while the repository stays private. Decide before opening it:
`futureinternet-17-00238-v2.pdf` is open access (MDPI, CC BY); check the other three, or untrack them.
