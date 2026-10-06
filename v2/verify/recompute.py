#!/usr/bin/env python3
"""Phase 4.1: every headline number, recomputed from raw records and read back out of the report.

Plan §7.1. Two independent derivations meet here. One recomputes a figure from the result files
the report cites. The other reads the figure the report states, at every place it is stated, with a
pattern that captures whatever is written there. A claim is EQUAL only when every stated copy matches
the recomputation, so this catches both a figure that disagrees with its data and copies that have
drifted apart (§7.31.12, and pass 3 of Stage 5).

A recomputation that cannot be made from committed files is reported as NO SOURCE, not skipped: that
is a finding about the evidence, whatever the figure.

Run from v2/:  python3 verify/recompute.py [--corpus DIR] [--corpus-uniform DIR] [--json OUT]
The corpora are needed only for the two survey claims; rebuild them with
`figures/fetch_hacs_corpus.py --rebuild`. Without them those claims print SKIPPED.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import statistics
import subprocess
import sys
from pathlib import Path

V2 = Path(__file__).resolve().parent.parent
EXP = V2 / "experiments"
REPORT = Path(__import__("os").environ.get("RECOMPUTE_REPORT", V2 / "report"))  # a copy, for the control
ARGS = argparse.Namespace(corpus=None, corpus_uniform=None)


def j(path: str):
    return json.loads((V2 / path).read_text())


def text(name: str) -> str:
    return (REPORT / name).read_text()


def abstract() -> str:
    t = text("00_front_matter.md")
    return t[t.index("## Abstract"):t.index("## Declaration")]


class Num(float):
    """A measured figure, equal to a stated copy when that copy is it rounded to the copy's precision."""
    def __new__(cls, value: float, unit: str):
        obj = super().__new__(cls, value)
        obj.unit = unit
        return obj

    def __str__(self) -> str:
        return f"{float(self):g} {self.unit}"

    def matches(self, written: str) -> bool:
        m = re.fullmatch(r"([\d.]+) ?(\S+)", written.strip())
        if not m or m.group(2) != self.unit:
            return False
        decimals = len(m.group(1).partition(".")[2])
        return round(float(self), decimals) == float(m.group(1))


class Pair(tuple):
    """Two figures stated in two places, in order."""
    def __new__(cls, *items):
        return super().__new__(cls, items)

    def __str__(self) -> str:
        return " | ".join(self)


Many = Pair


class NoSource(Exception):
    """The figure cannot be recomputed from anything committed."""


CLAIMS: list[dict] = []


def claim(cid: str, what: str, places: list[tuple[str, str]]):
    """Register a recomputation. `places`: (where, regex with one group capturing the stated value).

    `where` is a report file name, or "abstract". Every match of the regex in that place is checked.
    """
    def register(fn):
        CLAIMS.append({"id": cid, "what": what, "places": places, "compute": fn})
        return fn
    return register


def norm(written: str) -> str:
    """Bold removed, and a ` · `-separated list of counts compared as a set (its order is the writer's)."""
    written = written.replace("**", "").strip()
    if " · " in written:
        return " · ".join(sorted(written.split(" · ")))
    return written


def stated(where: str, pattern: str) -> list[str]:
    body = abstract() if where == "abstract" else text(where)
    return [m.group(1) for m in re.finditer(pattern, body, re.S)]


def compat_clean(path: str) -> tuple[int, int]:
    rows = j(path)["arm_a"]
    return sum(1 for r in rows if r.get("level") == "platforms_clean"), len(rows)


def pct(a: int, b: int) -> str:
    return f"{round(100 * a / b)}%"


# -- the abstract -------------------------------------------------------------------------------

@claim("A1.01", "active installations (Home Assistant analytics)",
       [("abstract", r"Home Assistant reports ([\d,]+) active installations")])
def _():
    return f"{j('figures/ecosystem_scale.json')['active_installations']:,}"


@claim("A1.11a", "distinct integrations measured across the two corpora (37 + 40, two shared)",
       [("abstract", r"Across (\d+) community integrations on two corpora"),
        ("08_conclusions.md", r"across (\d+) integrations on two corpora"),
        ("08_conclusions.md", r"measured at import for (\d+) integrations")])
def _():
    head = {r["domain"] for r in j("experiments/compat/results/hacs_corpus_manifest.json")["repositories"]
            if r.get("ok") and r.get("on_disk", True)}
    uni = {r["domain"] for r in j("experiments/compat/results/hacs_corpus_manifest_uniform.json")["repositories"]
           if r.get("ok")}
    shared = sorted(head & uni)
    return str(len(head | uni)), f"{len(head) + len(uni)} measurements; shared {shared}"


@claim("A1.11b", "share of members the two corpora have in common",
       [("07_evaluation.md", r"The corpora share (\d+%) of")])
def _():
    head = {r["domain"] for r in j("experiments/compat/results/hacs_corpus_manifest.json")["repositories"]
            if r.get("ok") and r.get("on_disk", True)}
    uni = {r["domain"] for r in j("experiments/compat/results/hacs_corpus_manifest_uniform.json")["repositories"]
           if r.get("ok")}
    return pct(len(head & uni), len(uni)), f"{len(head & uni)} of {len(uni)}"


@claim("A1.12", "clean in both arms: head corpus, then uniform",
       [("abstract", r"(\d+% and \d+%) clean in both arms")])
def _():
    hb, ht = compat_clean("experiments/compat/results/rerun_20261003/c1_baseline.json")
    hc, _ = compat_clean("experiments/compat/results/rerun_20261003/c1_declared_core.json")
    ub, ut = compat_clean("experiments/compat/results/rerun_20261003/uniform_baseline.json")
    uc, _ = compat_clean("experiments/compat/results/rerun_20261003/uniform_confined.json")
    detail = f"head {hb}/{ht} baseline, {hc}/{ht} confined; uniform {ub}/{ut}, {uc}/{ut}"
    if hb != hc or ub != uc:
        return "arms differ", detail
    return f"{pct(hb, ht)} and {pct(ub, ut)}", detail


@claim("A1.12b", "integrations failing confined but not unconfined, both corpora",
       [("abstract", r"attributable to the design number (\w+), twice")])
def _():
    out = []
    for base, conf in (("c1_baseline", "c1_declared_core"), ("uniform_baseline", "uniform_confined")):
        clean = lambda n: {r["domain"] for r in j(f"experiments/compat/results/rerun_20261003/{n}.json")["arm_a"]
                           if r.get("level") == "platforms_clean"}
        out.append(len(clean(base) - clean(conf)))
    return ("none" if out == [0, 0] else str(out)), f"set differences {out}"


@claim("A1.13", "integrations executed end to end (a named set)",
       [("abstract", r"(\w+) integrations were executed end to end")])
def _():
    # The named subjects of every end-to-end run in Chapter 7: §7.17's five, §7.27's nordpool,
    # §7.31's three, §7.34's pirateweather, then §7.40–§7.42's three.
    runs = {"7.17": ["scheduler", "adaptive_lighting", "thermal_comfort", "powercalc", "watchman"],
            "7.27": ["nordpool"], "7.31": ["smhi_brandrisk", "regensburg_transport", "dwd_weather"],
            "7.34": ["pirateweather"], "7.40": ["midea_ac_lan"], "7.41": ["localtuya"],
            "7.42": ["trakt_tv"]}
    n = sum(len(v) for v in runs.values())
    words = {10: "Ten", 13: "Thirteen"}
    return words.get(n, str(n)), f"{n}: " + "; ".join(f"§{k} {len(v)}" for k, v in runs.items())


@claim("A1.13b", "head-corpus integrations whose configuration asks for a credential",
       [("abstract", r"being that (\d+ of \d+) need a credential")])
def _():
    if ARGS.corpus is None:
        raise LookupError("needs --corpus")
    keys = re.compile(r"CONF_(API_KEY|TOKEN|ACCESS_TOKEN|PASSWORD|USERNAME|HOST|EMAIL)\b|"
                      r"[\"'](api_key|token|password|username|host|email)[\"']")
    dirs = sorted(p for p in Path(ARGS.corpus).iterdir() if p.is_dir())
    asking = [d.name for d in dirs if any(keys.search(f.read_text(errors="replace"))
                                          for f in d.rglob("*.py"))]
    return f"{len(asking)} of {len(dirs)}", ("whole-directory scan for credential fields; the "
                                             "survey script itself was never committed")


@claim("A1.18", "mediation latency, one client, median of the three verification passes",
       [("abstract", r"mediation costs ([\d.]+ µs)"),
        ("08_conclusions.md", r"Latency at 0\.009% utilisation \| \*\*([\d.]+ µs)\*\*")])
def _():
    stats = {s["id"]: s for s in j("experiments/verify/results/phase3_timing/stats.json")}
    # The claim is the three Phase 3 passes; the final tag's run (the fourth value) is checked
    # against it by timing_stats.py, not folded into the figure the report states.
    three = stats["latency_1"]["values"][:3]
    median = statistics.median(three)
    return Num(median, "µs"), f"{three} µs → median {median}"


@claim("A1.19", "durable record per decision, with fsync, median",
       [("abstract", r"records at ([\d.]+ ms)")])
def _():
    us = j("experiments/durability/results/pi5.json")["durability"]["with fsync (as built)"]["median"]
    return f"{us / 1000:.2f} ms", f"{us} µs"


@claim("A1.20", "headroom over realistic demand, the request and the durable record both counted",
       [("abstract", r"([\d]+×) clear of realistic demand"),
        ("08_conclusions.md", r"the mediator is ([\d]+×)\s+clear")])
def _():
    us = j("experiments/durability/results/pi5.json")["durability"]["with fsync (as built)"]["median"]
    stats = {s["id"]: s for s in j("experiments/verify/results/phase3_timing/stats.json")}
    per = us + stats["latency_1"]["median"]
    capacity = 1e6 / per
    demand = 26 * 5 / 30                     # §7.19.3: 26 sandboxes × 5 operations per 30 s
    return f"{int(capacity / demand)}×", f"{capacity:.0f}/s ÷ {demand:.2f}/s = {capacity / demand:.1f}"


@claim("A1.21", "thermal_comfort's entities in (A): registry rows, before and after a restart",
       [("07_evaluation.md", r"\*\*(\d+ of \d+)\*\* of `thermal_comfort`'s entities"),
        ("07_evaluation.md", r"no sandbox running \| (\d+ of \d+) rows remain")])
def _():
    n = j("experiments/real_platform/results/w1_step2_20261004/names_and_restart.json")
    return (f"{n['rows_after_restart']} of {n['entities']}",
            f"rows after restart {n['rows_after_restart']}, states identical "
            f"{n['states_identical_after_restart']}, entities {n['entities']}")


@claim("A1.22", "change in (A) to the mediator's push: the worst of 30, in the run behind the median",
       [("07_evaluation.md", r"0\.71 ms median this row quotes had a worst case of \*\*([\d.]+ ms)\*\*"),
        ("07_evaluation.md", r"The run its 0\.71 ms median comes from had a worst case of ([\d.]+ ms)")])
def _():
    worst = []
    for log in sorted(EXP.glob("real_platform/results/**/*real_platform*.log")) + \
            sorted(p for p in EXP.glob("verify/results/**/*real_platform*.log") if "mutants" not in p.parts):
        for m in re.finditer(r"R5:.*median ([\d.]+) ms, max ([\d.]+) ms", log.read_text()):
            worst.append((float(m.group(1)), float(m.group(2)), log.relative_to(EXP).as_posix()))
    behind = [w for w in worst if w[0] == 0.71]
    if not behind:
        raise NoSource("no committed log has a 0.71 ms median")
    return f"{behind[0][1]} ms", (f"{behind[0][2]}; worst across all {len(worst)} committed runs "
                                  f"{min(w[1] for w in worst)}–{max(w[1] for w in worst)} ms")


@claim("A1.23", "a user's command to the integration's own code, the range over four runs (F44)",
       [("abstract", r"integration's own code in (\d+ to \d+ ms)")])
def _():
    stats = {s["id"]: s for s in j("experiments/verify/results/phase3_timing/stats.json")}
    runs = [v for v in stats["command"]["values"] if v is not None]
    return (f"{round(min(runs))} to {round(max(runs))} ms",
            f"Phase 3's three passes and the final tag: {[round(v, 1) for v in runs]} ms")


@claim("A1.24", "refusals before the cut-off, and its time on disk",
       [("abstract", r"stopped after (\d+) of them")])
def _():
    log = (EXP / "flood/results/pi_20261005/selftest_flood_disk.log").read_text()
    n = re.search(r"exactly (\d+) refusals are on disk", log).group(1)
    t = re.search(r"flood start to cut-off ([\d.]+) s", log).group(1)
    return n, f"{n} refusals, cut-off after {t} s"


@claim("A1.25", "self-test suites",
       [("abstract", r"([\w-]+) self-test suites and\s+the base self-test pass")])
def _():
    n = len(list((V2 / "framework/confine").glob("selftest_*.py")))
    return {25: "Twenty-five"}.get(n, str(n)), (f"{n} `selftest_*.py`, the front matter's definition of "
                                                f"a suite, and the base `selftest.py` apart")


def suites_at(rev: str) -> int:
    """`selftest_*.py` only: the convention the report used for its counts until 2026-10-05."""
    out = subprocess.run(["git", "-C", str(V2), "ls-tree", "--name-only", rev, "framework/confine/"],
                         capture_output=True, text=True, check=True).stdout
    return sum(1 for p in out.split() if re.search(r"/selftest_[^/]*\.py$", p))


@claim("A1.29", "suites that existed when §7.27 found the Zeroconf failure",
       [("abstract", r"behind (\w+) suites that all passed")])
def _():
    rev = subprocess.run(["git", "-C", str(V2), "log", "--format=%h", "-1", "-S", "### 7.27",
                          "--", "report/07_evaluation.md"], capture_output=True, text=True).stdout.split()
    rev = rev[-1] if rev else None
    if not rev:
        raise NoSource("no commit introduces §7.27")
    n = suites_at(rev)
    return {18: "eighteen"}.get(n, str(n)), (f"{n} `selftest_*.py` at {rev}, the commit that wrote "
                                             f"§7.27 ({n + 1} with the base `selftest.py`)")


@claim("A1.30", "suites that existed when §7.31 found three further defects",
       [("abstract", r"behind (\w+) passing suites")])
def _():
    rev = subprocess.run(["git", "-C", str(V2), "log", "--format=%h", "-1", "-S", "## 7.31",
                          "--", "report/07_evaluation.md"], capture_output=True, text=True).stdout.split()
    if not rev:
        raise NoSource("no commit introduces §7.31")
    n = suites_at(rev[-1])
    return {20: "twenty", 21: "twenty-one"}.get(n, str(n)), (f"{n} `selftest_*.py` at {rev[-1]}, the "
                                                             f"commit that wrote §7.31 ({n + 1} with the "
                                                             f"base `selftest.py`)")


@claim("A1.29b", "share of the head corpus that the egress design serves (cloud iot_class)",
       [("abstract", r"unusable for the (\d+%) of the corpus")])
def _():
    if ARGS.corpus is None:
        raise LookupError("needs --corpus")
    iot = collections.Counter(json.loads((d / "manifest.json").read_text()).get("iot_class")
                              for d in Path(ARGS.corpus).iterdir() if d.is_dir())
    cloud = iot["cloud_polling"] + iot["cloud_push"]
    return pct(cloud, sum(iot.values())), f"{cloud} of {sum(iot.values())}: {dict(iot)}"


# -- Chapter 8, §8.2: the three assertions' tables ----------------------------------------------

@claim("8.2.1a", "garbage-collector technique: ways the token was reached unconfined",
       [("08_conclusions.md", r"\*\*reached it (\d+) ways\*\*")])
def _():
    return str(j("experiments/gc_attack/results/rerun_20261003/pi5_s1.json")["unconfined"]["gc_hit_count"])


@claim("8.2.1b", "garbage-collector technique: objects the confined walk saw, all its own",
       [("08_conclusions.md", r"\| ([\d,]+) objects, all its own")])
def _():
    c = j("experiments/gc_attack/results/rerun_20261003/pi5_s1.json")["confined"]
    return f"{c['heap_size']:,}", f"hits {c['gc_hit_count']}, mediator holds it {c['mediator_holds_credential']}"


def adversary_lines(name: str) -> list[str]:
    return (EXP / f"adversary_baseline/results/{name}").read_text().splitlines()


@claim("8.2.1c", "2021 file-theft canaries recovered, unconfined then confined",
       [("08_conclusions.md", r"\*\*(\d+ of \d+) recovered\*\*"),
        ("08_conclusions.md", r"traversals worked \| \*\*(\d+ of \d+)\*\*")])
def _():
    found = lambda name: {m.group(0) for line in adversary_lines(name)
                          for m in re.finditer(r"CANARY-[A-Z]+", line)}
    unconfined, confined = found("pi5_unconfined.txt"), found("pi5_confined.txt")
    return Pair(f"{len(unconfined)} of 2", f"{len(confined)} of 2"), f"{sorted(unconfined)}; confined {sorted(confined)}"


@claim("8.2.1d", "file-theft attempts that worked unconfined",
       [("08_conclusions.md", r"recovered\*\*; (\w+) traversals worked")])
def _():
    lines = adversary_lines("pi5_unconfined.txt")
    end = next(i for i, l in enumerate(lines) if "another process's environ" in l)
    n = sum(1 for l in lines[:end] if "LEAKED" in l)
    return {5: "five"}.get(n, str(n)), f"{n} LEAKED lines before the process probes"


@claim("8.2.1e", "undeclared entity states readable: all, then presence; unconfined then confined",
       [("08_conclusions.md", r"\| \*\*(\d+ of \d+)\*\*, and \*\*\d+ of \d+\*\* that disclose"),
        ("08_conclusions.md", r"\*\*\d+ of \d+\*\*, and \*\*(\d+ of \d+)\*\* that disclose"),
        ("08_conclusions.md", r"presence \| \*\*(\d+ of \d+)\*\*, \*\*\d+ of \d+\*\* \|"),
        ("08_conclusions.md", r"presence \| \*\*\d+ of \d+\*\*, \*\*(\d+ of \d+)\*\* \|")])
def _():
    sys.path.insert(0, str(V2 / "framework"))
    from confine import home
    d = j("experiments/entity_visibility/results/rerun_20261003/pi5_s3.json")
    sensitive, total = set(home.sensitive_ids()), len(home.entity_ids())
    u, c = set(d["unconfined"]["visible"]), set(d["confined"]["visible"])
    return Many(f"{len(u)} of {total}", f"{len(u & sensitive)} of {len(sensitive)}",
                f"{len(c)} of {total}", f"{len(c & sensitive)} of {len(sensitive)}"), \
        f"sensitive marked in confine/home.py: {len(sensitive)}"


@claim("8.2.2", "import-level compatibility, both arms, both corpora (the §8.2.2 table)",
       [("08_conclusions.md", r"Head-weighted, 37 \| (\d+%) \| \*\*\d+%\*\*"),
        ("08_conclusions.md", r"Head-weighted, 37 \| \d+% \| \*\*(\d+%)\*\*"),
        ("08_conclusions.md", r"Uniform draw, 40 \| (\d+%) \| \*\*\d+%\*\*"),
        ("08_conclusions.md", r"Uniform draw, 40 \| \d+% \| \*\*(\d+%)\*\*")])
def _():
    out = []
    for conf, base in (("c1_declared_core", "c1_baseline"), ("uniform_confined", "uniform_baseline")):
        for name in (conf, base):
            a, b = compat_clean(f"experiments/compat/results/rerun_20261003/{name}.json")
            out.append(pct(a, b))
    return Many(*out), "head confined, head baseline, uniform confined, uniform baseline"


@claim("8.2.3a", "mean community integrations per HACS-running installation",
       [("08_conclusions.md", r"a measured mean of \*\*([\d.]+)\*\* integrations")])
def _():
    return str(j("figures/ecosystem_scale.json")["mean_custom_integrations_per_hacs_installation"])


@claim("8.2.3b", "mediator capacity with the durable record and the request counted",
       [("08_conclusions.md", r"\*\*(\d+) decisions/s\*\*"),
        ("08_conclusions.md", r"does not draw on the (\d+) decisions/s")])
def _():
    us = j("experiments/durability/results/pi5.json")["durability"]["with fsync (as built)"]["median"]
    stats = {s["id"]: s for s in j("experiments/verify/results/phase3_timing/stats.json")}
    return str(int(1e6 / (us + stats["latency_1"]["median"]))), "§7.45.1's arithmetic"


@claim("8.2.3c", "durable record against the non-durable write",
       [("08_conclusions.md", r"costs \*\*3\.67 ms\*\*, (\d+×) the non-durable")])
def _():
    d = j("experiments/durability/results/pi5.json")["durability"]
    r = d["with fsync (as built)"]["median"] / d["without fsync"]["median"]
    return f"{int(r)}×", f"{r:.1f}"


@claim("8.2.3d", "mediator cost per delivered push (§7.36's suite log)",
       [("08_conclusions.md", r"\*\*([\d.]+ µs)\*\* per delivered state change")])
def _():
    log = (EXP / "push_loop/results/w1_step1_20261004/suites/selftest_push.log").read_text()
    us = float(re.search(r"([\d.]+) µs per push", log).group(1))
    stats = {s["id"]: s for s in j("experiments/verify/results/phase3_timing/stats.json")}
    return Num(us, "µs"), f"re-measured in the verification passes: {stats['push_cost']['values']} µs"


# -- Chapter 7, one headline per results section ------------------------------------------------

def outcome_counts(name: str) -> str:
    line = next(l for l in adversary_lines(name)
                if re.match(r"^\s*((BLOCKED|DENY|EMPTY|LEAKED|PERMIT|NOT RUN|UNMEDIATED)\s+\d+\s*){2,}$", l))
    return " · ".join(f"{k} {v}" for k, v in re.findall(r"(BLOCKED|DENY|EMPTY|LEAKED|PERMIT|NOT RUN|UNMEDIATED)\s+(\d+)", line))


def bold_free(written: str) -> str:
    return written.replace("**", "")


@claim("7.13", "adversary outcome counts, unconfined then confined",
       [("07_evaluation.md", r"\| Outcome counts \| ([^|]+?) \|"),
        ("07_evaluation.md", r"\| Outcome counts \| [^|]+ \| ([^|]+?) \|")])
def _():
    return Pair(outcome_counts("pi5_unconfined.txt"), outcome_counts("pi5_confined.txt")), \
        "from each log's summary line; compared as sets of counts, the table orders them differently"


@claim("7.13b", "attacks that returned data, unconfined then confined",
       [("07_evaluation.md", r"\| Attacks that returned data \| (\d+) \|"),
        ("07_evaluation.md", r"\| Attacks that returned data \| \d+ \| (\d+) \|")])
def _():
    leaked = lambda n: sum(1 for l in adversary_lines(n) if "LEAKED" in l and not re.match(r"^\s*BLOCKED", l))
    return Pair(str(leaked("pi5_unconfined.txt")), str(leaked("pi5_confined.txt")))


@claim("7.29", "C1: trees hashed before and after, and with changed source, per arm",
       [("07_evaluation.md", r"\| Trees hashed before and after \| \*\*(\d+)\*\*"),
        ("07_evaluation.md", r"\| Trees hashed before and after \| \*\*\d+\*\* \| \*\*(\d+)\*\*"),
        ("07_evaluation.md", r"\*\*([\w-]+) tree comparisons, zero source changes")])
def _():
    a = j("experiments/compat/results/c1_baseline.json")["c1"]
    b = j("experiments/compat/results/c1_declared_core.json")["c1"]
    total = a["integrations_checked"] + b["integrations_checked"]
    changed = a["source_changed"] + b["source_changed"] + a["total_diff_lines"] + b["total_diff_lines"]
    return Pair(str(a["integrations_checked"]), str(b["integrations_checked"]),
                {75: "Seventy-five"}.get(total, str(total))), f"changed source and diff lines in all: {changed}"


@claim("7.33", "uniform corpus: share of integrations using services, config, bus",
       [("07_evaluation.md", r"\| `services` \| [\d.]+% \| \*\*([\d.]+%)\*\*"),
        ("07_evaluation.md", r"\| `config` \| [\d.]+% \| \*\*([\d.]+%)\*\*"),
        ("07_evaluation.md", r"\| `bus` \| [\d.]+% \| \*\*([\d.]+%)\*\*")])
def _():
    share = j("figures/api_surface_uniform.json")["handle_share"]
    return Pair(f"{share['services']}%", f"{share['config']}%", f"{share['bus']}%"), \
        f"n = {j('figures/api_surface_uniform.json')['n']}"


@claim("7.33b", "head corpus (144): share using services, config, bus",
       [("07_evaluation.md", r"\| `services` \| ([\d.]+%) \|"),
        ("07_evaluation.md", r"\| `config` \| ([\d.]+%) \|"),
        ("07_evaluation.md", r"\| `bus` \| ([\d.]+%) \|")])
def _():
    a = j("figures/api_surface_hacs.json")
    return Pair(f"{a['handle_share']['services']}%", f"{a['handle_share']['config']}%",
                f"{a['handle_share']['bus']}%"), \
        f"n = {a['n']}; recomputed from the committed per-integration results, the source sample itself is not kept (F16)"


def bytecode(mode: str) -> dict:
    return j(f"experiments/bytecode_cache/results/w2c_20261004/matrix/powercalc_{mode}.json")


@claim("7.39", "powercalc: time to report, as installed, compiled at install, empty cache",
       [("07_evaluation.md", r"\| as installed today \|(?: [^|]+ \|){5} ([\d.]+ s) \|"),
        ("07_evaluation.md", r"\| compiled at install \|(?: [^|]+ \|){5} \*\*([\d.]+ s)\*\* \|"),
        ("07_evaluation.md", r"\| control: empty cache \|(?: [^|]+ \|){5} ([\d.]+ s) \|")])
def _():
    out, cache = [], []
    for mode in ("default", "compiled", "cold"):
        d = bytecode(mode)
        b = (d[0] if isinstance(d, list) else d)["bytecode"]
        out.append(f"{b['seconds_since_start']:.2f} s")
        g = b["groups"]
        cache.append(f"{mode}: deps {g['deps']['from_cache']}/{g['deps']['from_cache'] + g['deps']['compiled']}, "
                     f"component {g['component']['from_cache']}/{g['component']['from_cache'] + g['component']['compiled']}")
    return Pair(*out), "; ".join(cache)


@claim("7.44", "the flood on disk: cut-off time, refusals, neighbour's answers and slowest, Repairs",
       [("07_evaluation.md", r"cut off within \*\*([\d.]+ s)\*\*; exactly"),
        ("07_evaluation.md", r"exactly \*\*(\d+)\*\* refusals on disk"),
        ("07_evaluation.md", r"answered \*\*(\d+)\*\* times, every answer a grant"),
        ("07_evaluation.md", r"the slowest \*\*([\d.]+ ms)\*\*"),
        ("07_evaluation.md", r"issue in \(A\) within \*\*(\d+ ms)\*\*")])
def _():
    flood = (EXP / "flood/results/pi_20261005/selftest_flood_disk.log").read_text()
    house = (EXP / "flood/results/pi_20261005/selftest_real_platform.log").read_text()
    cut = float(re.search(r"cut off\s+—\s+after ([\d.]+) s", flood).group(1))
    n = re.search(r"exactly (\d+) refusals are on disk", flood).group(1)
    answers, worst = re.search(r"(\d+) answers, worst ([\d.]+) ms", flood).groups()
    repairs = re.search(r"within 1 s of the cut-off\s+—\s+(\d+) ms", house).group(1)
    return Pair(f"{cut:.2f} s", n, answers, f"{worst} ms", f"{repairs} ms"), \
        "selftest_flood_disk.log (on disk) and selftest_real_platform.log, 2026-10-05"


@claim("7.22", "S9's CPU cap: share consumed, the run the report quotes, and the spread of every committed run",
       [("07_evaluation.md", r"\*\*([\d.]+%) consumed over [\d.]+ s, [\d.]+ s throttled\*\*")])
def _():
    runs = [(float(m.group(1)), log.relative_to(EXP).as_posix())
            for log in EXP.glob("**/selftest_resources.log") if "mutants" not in log.parts
            for m in re.finditer(r"consumed ([\d.]+)% of one processor", log.read_text())]
    spread = (min(r[0] for r in runs), max(r[0] for r in runs))
    if not any(r[0] == 25.1 for r in runs):
        raise NoSource("no committed run consumed 25.1%")
    within = all(abs(r[0] - 25) <= 2 for r in runs)
    return "25.1%", f"{len(runs)} committed runs, {spread[0]}–{spread[1]}%, all within ±2 points of the cap: {within}"


@claim("7.31.11", "aiodns share of resolutions on a /16, and its counts",
       [("07_evaluation.md", r"Today the same count is \*\*(\d+%)\*\*, \d+ against \d+"),
        ("07_evaluation.md", r"Today the same count is \*\*\d+%\*\*, (\d+ against \d+)")])
def _():
    d = j("experiments/egress_shape/results/rerun_20261003/pi5_egress_shape.json")
    counts = collections.Counter()
    for report in d["reports"]:
        counts.update(report["netshape"].get("resolution", {}))
    aiodns, other = counts["aiodns.getaddrinfo"], counts["getaddrinfo"]
    return Pair(pct(aiodns, aiodns + other), f"{aiodns} against {other}"), \
        f"{len(d['reports'])} integrations; the same counting as §7.24.2's 3,073 against 120"


@claim("7.14", "entity visibility in §7.14's own table and §7.26.3's T06 row, against the same data",
       [("07_evaluation.md", r"\| \*\*Entities present to it\*\* \| \*\*(\d+ / \d+)\*\*"),
        ("07_evaluation.md", r"\| \*\*Entities present to it\*\* \| \*\*\d+ / \d+\*\* \| \*\*(\d+ / \d+)\*\*"),
        ("07_evaluation.md", r"\| \*\*Of those, occupancy or presence\*\* \| \*\*(\d+ / \d+)\*\*"),
        ("07_evaluation.md", r"\| \*\*Of those, occupancy or presence\*\* \| \*\*\d+ / \d+\*\* \| \*\*(\d+ / \d+)\*\*"),
        ("07_evaluation.md", r"§7\.14\.2: \*\*(\d+/\d+ → \d+/\d+)\*\*, and"),
        ("07_evaluation.md", r"and \*\*(\d+/\d+ → \d+/\d+)\*\* presence entities")])
def _():
    sys.path.insert(0, str(V2 / "framework"))
    from confine import home
    d = j("experiments/entity_visibility/results/rerun_20261003/pi5_s3.json")
    sens, total = set(home.sensitive_ids()), len(home.entity_ids())
    u, c = set(d["unconfined"]["visible"]), set(d["confined"]["visible"])
    return Pair(f"{len(u)} / {total}", f"{len(c)} / {total}", f"{len(u & sens)} / {len(sens)}",
                f"{len(c & sens)} / {len(sens)}", f"{len(u)}/{total} → {len(c)}/{total}",
                f"{len(u & sens)}/{len(sens)} → {len(c & sens)}/{len(sens)}")


@claim("7.36", "undeclared changes delivered to the confined subscriber, and with the filter bypassed",
       [("07_evaluation.md", r"subscription half is now a delivered and filtered stream: \*\*(\d+ of \d+)\*\*")])
def _():
    log = (EXP / "push_loop/results/w1_step1_20261004/suites/selftest_push.log").read_text()
    n = re.search(r"(\d+ of \d+) undeclared changes delivered", log).group(1)
    seen = re.search(r"table bypassed.*?(\d+ of \d+) seen", log).group(1)
    return n, f"with the subscription table bypassed: {seen} seen (the suite's own control)"


# -----------------------------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--corpus", type=Path)
    ap.add_argument("--corpus-uniform", type=Path)
    ap.add_argument("--json", type=Path)
    ap.parse_args(namespace=ARGS)
    rows, tally = [], collections.Counter()
    for c in CLAIMS:
        try:
            got = c["compute"]()
            value, detail = (got, "") if isinstance(got, (str, Pair)) else got
        except NoSource as err:
            value, detail, status = None, str(err), "NO SOURCE"
        except LookupError as err:
            value, detail, status = None, str(err), "SKIPPED"
        copies = [(where, s) for where, pattern in c["places"] for s in stated(where, pattern)]
        expected = None
        if isinstance(value, Pair):
            # One recomputed figure per place, in order; a place stated more than once is checked each time.
            expected = [v for (where, pattern), v in zip(c["places"], value)
                        for _ in stated(where, pattern)]
        if value is not None:
            if not copies or (expected is not None and len(c["places"]) != len(value)):
                status = "NOT FOUND"
            elif expected is not None and all(norm(s) == norm(e) for (_, s), e in zip(copies, expected)) \
                    and all(stated(w, p) for w, p in c["places"]):
                status = "EQUAL"
            elif expected is not None:
                status = "DIFFERS"
            elif all((value.matches(s) if isinstance(value, Num) else s == value) for _, s in copies):
                status = "EQUAL"
            else:
                status = "DIFFERS"
        tally[status] += 1
        rows.append({"id": c["id"], "what": c["what"], "recomputed": None if value is None else str(value),
                     "detail": detail,
                     "stated": copies, "status": status})
        shown = ", ".join(f"{w}: {s}" for w, s in copies) or "—"
        print(f"{status:<10} {c['id']:<7} {c['what']}\n"
              f"           recomputed {value}  ({detail})\n           stated     {shown}")
    print("\n" + ", ".join(f"{k} {v}" for k, v in sorted(tally.items())))
    if ARGS.json:
        ARGS.json.write_text(json.dumps(rows, indent=1))
    return 0 if set(tally) <= {"EQUAL", "SKIPPED"} else 1


if __name__ == "__main__":
    sys.exit(main())
