# Reproducing the evaluation, from a blank Raspberry Pi

This guide builds, from nothing, the environment every command in `experiments/` and every suite in
`framework/` assumes, and then runs the suites. It was written on 2026-10-06 (verification finding
F18) because no such guide existed. Until then, that environment lived only on the author's Pi,
built by hand over six weeks.

**Status.** Every step below was checked against the Pi the report was measured on: each recorded
command matches what is installed there. Two of the commands (steps 6 and 7) were *reconstructed*
from what the directories contain, because nobody wrote them down at the time, and they say so. **The
guide has not yet been followed from a freshly imaged card**, which is its real test (F18, waiting on
a spare card). Until it has, treat a step that fails as a finding about the guide, not about you.

Every step ends with a **Check**, so you can tell the step worked before the next one depends on it.

## What you need

| | Used for every figure in the report |
|---|---|
| Board | Raspberry Pi 5, 4 GB (the C4 hardware, §3.4) |
| OS | Raspberry Pi OS 64-bit, Debian 13 *trixie*; kernel `6.12.47+rpt-rpi-2712` |
| Storage | about 2 GB free on the card, beyond the OS |
| Network | outbound internet (corpus, packages, three integrations' real APIs) |
| Supervisor interpreter | the OS's own `python3` (3.13.5 on trixie). The framework is standard library only |
| Platform interpreter | Python 3.14.7 with Home Assistant 2026.8.3, built in step 4 |

The code expects its supporting directories under `~/r2exp/` (several modules default to those paths),
so this guide keeps that layout. The repository itself can live anywhere; below it is `~/ha_security`.

## 1. The memory controller

Raspberry Pi OS starts the kernel with `cgroup_disable=memory`, so nothing can bound a sandbox's memory
and the framework refuses to start (S9, N3). The parameter comes from the firmware, not from
`cmdline.txt`, so there is nothing to remove. Append the enable instead, on the file's single line:

```bash
sudo sed -i '1 s/$/ cgroup_enable=memory cgroup_memory=1/' /boot/firmware/cmdline.txt
sudo reboot
```

**Check:** `cat /sys/fs/cgroup/user.slice/user-$(id -u).slice/user@$(id -u).service/cgroup.controllers`
lists `memory` (the Pi prints `cpu memory pids`). Background: `experiments/host_isolation_probe/README.md`.

## 2. The code

```bash
git clone https://github.com/Speedylo/ha_security.git ~/ha_security
cd ~/ha_security/v2
```

The evaluation was frozen at two tags: `verify-2026-10`, where every measurement was re-run, and
`verify-2026-10-f03`, which has the one fix the verification campaign made to the framework (§7.45.2).
`main` has both, plus the documents written since.

**Check:** `git log -1 --oneline` prints a commit, and `ls framework/confine | wc -l` is about 60.

## 3. `uv`

`uv` builds the interpreter and installs every package below. The Pi has 0.12.5 at `~/.local/bin/uv`,
which is where the framework looks for it by default.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Check:** `~/.local/bin/uv --version`.

## 4. Python 3.14 and Home Assistant 2026.8.3 (`~/r2exp/ha314`)

Home Assistant 2026.8 needs Python 3.14.2 or later, newer than trixie's. This is the interpreter every
sandbox runs (`--python` throughout). Recorded in `experiments/r2_footprint/README.md`:

```bash
mkdir -p ~/r2exp && cd ~/r2exp
~/.local/bin/uv venv --python 3.14 ha314
VIRTUAL_ENV=$PWD/ha314 ~/.local/bin/uv pip install "homeassistant==2026.8.3"
```

**Check:** `~/r2exp/ha314/bin/python -c "import homeassistant.const as c; print(c.__version__)"` prints
`2026.8.3`, and `~/r2exp/ha314/bin/python --version` prints 3.14.x (3.14.7 on the Pi). The Pi's
environment has 104 packages (`uv pip list --python ~/r2exp/ha314/bin/python | wc -l`).

## 5. The platform's own packages (`~/r2exp/platform-deps`)

The `default_config` closure's requirements, which a real installation has and a bare `pip install
homeassistant` does not (§6.14). Derived from the platform's own source, not typed: recorded in
`experiments/compat/README.md`.

```bash
cd ~/ha_security/v2/framework
python3 -m confine.compat --python ~/r2exp/ha314/bin/python --corpus /dev/null \
    --print-core-requirements > ~/r2exp/core-reqs.txt
~/.local/bin/uv pip install --python ~/r2exp/ha314/bin/python --target ~/r2exp/platform-deps \
    $(tr '\n' ' ' < ~/r2exp/core-reqs.txt)
```

**Check:** `core-reqs.txt` has 39 lines, and `ls ~/r2exp/platform-deps | grep -c dist-info` is 113 on the
Pi (about 670 MB). The 39 are pinned; what they pull in is not, so a later install can differ in
transitive versions (finding F13; `aiohttp` moved 3.14.3 → 3.14.4 between runs on the Pi).

## 6. The un-stripping set (`~/r2exp/t2/platform-deps-aug`)

The six packages §6.12's un-stripping series adds, used by the depth runs (`experiments/unstrip/`,
§7.20.3, §7.35). *Reconstructed:* the directory holds exactly these six and nothing they depend on, so
it was installed with `--no-deps`; the versions are the ones `experiments/unstrip/README.md` records.

```bash
~/.local/bin/uv pip install --python ~/r2exp/ha314/bin/python --target ~/r2exp/t2/platform-deps-aug \
    --no-deps PyTurboJPEG==1.8.3 RestrictedPython==8.1 av==17.0.1 \
    home-assistant-frontend==20260729.7 numpy==2.3.2 paho-mqtt==2.1.0
```

**Check:** `ls ~/r2exp/t2/platform-deps-aug | grep -c dist-info` is 6.

## 7. Two experiment-specific sets

**(A)'s frontend (`~/r2exp/houseA-deps`)**, needed by every run against the house's real Home Assistant
(§7.37 on). Recorded in `framework/confine/house_a.py`:

```bash
~/.local/bin/uv pip install --python ~/r2exp/ha314/bin/python --target ~/r2exp/houseA-deps --no-deps \
    home-assistant-frontend==20260729.7 hassil==3.11.0 home-assistant-intents==2026.7.30 \
    unicode-rbnf==2.4.0 PyTurboJPEG==1.8.3 numpy==2.3.2 ha-ffmpeg==3.2.2 mutagen==1.48.1 \
    pymicro-vad==1.0.1 pyspeex-noise==1.0.2 async-timeout==4.0.3
```

**The fake air conditioner's library (`~/r2exp/t2/midea-src`)**, for §7.40 only. *Reconstructed:* the
directory holds `midea-lan` 2026.8.0 and its 16 dependencies, so it was installed with them:

```bash
~/.local/bin/uv pip install --python ~/r2exp/ha314/bin/python --target ~/r2exp/t2/midea-src midea-lan==2026.8.0
```

**Check:** 11 and 17 `dist-info` directories respectively. **§7.40 also has the Pi's LAN address written
into its code** (`LAN = "10.126.83.113"` in `framework/confine/endtoend_local.py`, and the
`fake_midea.py` command in `experiments/local_tcp/README.md`): change both to your own address.

## 8. The two corpora (`~/r2exp/corpus`, `~/r2exp/corpus_uniform`)

The community integrations every compatibility figure is measured on. Each manifest records the
commit every repository was fetched at, and `--rebuild` fetches exactly those (finding F21: until
2026-10-06 the manifests named only `HEAD`, and the commits were recovered by an exact match).

```bash
cd ~/ha_security/v2
python3 figures/fetch_hacs_corpus.py --rebuild experiments/compat/results/hacs_corpus_manifest.json --out ~/r2exp/corpus
python3 figures/fetch_hacs_corpus.py --rebuild experiments/compat/results/hacs_corpus_manifest_uniform.json --out ~/r2exp/corpus_uniform
```

**Check:** both end with every line `ok`, and the directories hold 37 and 40 integrations. Rebuilt this
way on the Pi, both were identical to the copies measured, file for file
(`experiments/verify/results/phase4/pin_corpus/README.md`).

## 9. (A), the house's real Home Assistant

Every run from §7.37 on acts on a real Home Assistant, (A), not the stand-in. `house_a` creates its
configuration in `~/r2exp/houseA`, onboards an owner, installs the bridge integration, and writes a
long-lived token to `~/.config/capstone/house_a.token` (mode 600; it is printed nowhere).

```bash
cd ~/ha_security/v2/framework
python3 -m confine.house_a up --fresh
```

**Check:** it prints `(A) up on http://127.0.0.1:8123 … bridge entry present`, and
`python3 -m confine.house_a status` prints `up`. To use (A) from a browser on another machine:
`ssh -L 8123:127.0.0.1:8123 <pi>`, then log in as `capstone` / `capstone-house-a` (a test owner on a
loopback-only instance, written in `house_a.py`).

## 10. The preflight, then every suite

Sandboxes can only be placed from inside the cgroup subtree systemd delegates to your user, so every
command that builds one runs under `systemd-run --user --scope` (§6.4.1). From a plain ssh shell the
preflight is *expected* to fail at `supervisor inside it`; that is the check working.

```bash
cd ~/ha_security/v2/framework
systemd-run --user --scope -q python3 -m confine.preflight
cd ~/ha_security/v2
bash experiments/selftests/suites_all.sh ~/r2exp/suites
cat ~/r2exp/suites/summary.txt
```

**Check:** the preflight exits 0, and every one of the 26 lines in `summary.txt` reads `exit=0`. The
whole run takes about two minutes. One known caveat: `selftest`'s "the user's home directory: ABSENT"
row fails if `TMPDIR` points under your home directory, because the test's configuration root is then
itself under home (F10). Leave `TMPDIR` unset.

## 11. The experiments

Each directory in `experiments/` has a README stating what it measured, the command, and where its
results are. Run them from `v2/framework` unless the README says otherwise.

| Directory | Report section |
|---|---|
| `host_isolation_probe`, `cgroup_placement` | §5.7.4, §6.4 |
| `mediation_latency` | §5.11.4, §7.19 (re-measured in §7.45.1) |
| `r2_footprint`, `base_component`, `unstrip` | §5.6, Chapter 6, §6.12, §7.20.3, §7.35 |
| `compat` | §6.12, §7.12, §7.23, §7.29, §7.31 |
| `adversary_baseline` | §7.13 |
| `entity_visibility` | §7.14 |
| `gc_attack` | §7.15 |
| `end_to_end` | §7.17, §7.31 |
| `egress_demand`, `egress_shape` | §7.18, §7.24, §7.31.11 |
| `durability` *(no README yet, F07)* | §7.20.1 |
| `push_loop`, `real_platform` | §7.36, §7.37, §7.38 |
| `bytecode_cache` | §7.39 |
| `local_tcp` | §7.40 (needs step 7's LAN change) |
| `oauth` | §7.42 (needs a Trakt account) |
| `flood` | §7.44 |
| `verify` | §7.45, the verification campaign |

**Credentials, for three runs only.** Nothing else needs an account. Each lives in
`~/.config/capstone/`, mode 600, and is never printed or committed:

- `house_a.token`, written by step 9;
- `pirateweather.key`, a free Pirate Weather API key, for the credentialed `pirateweather` run (§7.31);
- `trakt.json`, from `experiments/oauth/trakt_device_login.py` with your own free Trakt account (§7.42).

## Where this guide is known to be incomplete

- It has not been followed from a freshly imaged card (F18).
- Two install commands are reconstructed from directory contents (steps 6 and 7).
- §7.40's LAN address is in the code (step 7).
- Transitive package versions are not pinned (step 5, F13).
- The 150-integration sample behind contribution 1's API-surface figures was never kept and cannot be
  rebuilt (F16).
- The repository is private on GitHub. An examiner needs access, or an archive.
