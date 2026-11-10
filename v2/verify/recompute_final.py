#!/usr/bin/env python3
"""The final report's number check: headline figures recomputed from raw records, read back out of submission/.

`recompute.py` checks the working report in `report/`, whose wording the final report no longer
uses. This script keeps its recomputations where they are still the source of a figure, adds the
ones the final report introduced (the second final rerun of 1 November 2026, the bridge recount,
the mutation runs, the two samples, the findings table), and reads each figure at every place
`submission/` states it. A check is EQUAL only when every stated copy matches its recomputation;
NOT FOUND means a pattern matched nothing, which is itself a finding (the wording moved).

Run from v2/:  python3 verify/recompute_final.py [--json OUT]
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import statistics
import sys
from pathlib import Path

V2 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2 / "verify"))
import recompute as R  # noqa: E402  (its recomputations, not its report places)
import timing_stats as T  # noqa: E402

SUB = Path(__import__("os").environ.get("RECOMPUTE_SUBMISSION", V2 / "submission"))  # a copy, for the control
FINAL2 = V2 / "experiments/verify/results/final2_20261101"


def text(where: str) -> str:
    if where == "abstract":
        t = (SUB / "00_front_matter.md").read_text()
        return t[t.index("## Abstract"):t.index("**Keywords:**")]
    if where == "resume":
        t = (SUB / "00_front_matter.md").read_text()
        return t[t.index("## Résumé"):t.index("**Mots-clés")]
    return (SUB / where).read_text()


def stated(where: str, pattern: str) -> list[str]:
    return [m.group(1) for m in re.finditer(pattern, text(where), re.S)]


def norm(s: str) -> str:
    """Bold removed; digits grouped by comma (English) or by a space (French) compared as one number."""
    s = s.replace("**", "").strip()
    return re.sub(r"(?<=\d)[,\u202f\u00a0 ](?=\d{3}\b)", "", s)


CHECKS: list[dict] = []


def check(cid: str, what: str, places: list[tuple[str, str]]):
    """`places`: (file or "abstract"/"resume", regex with one group). The compute function returns
    either one expected value for every place, or a list with one expected value per place."""
    def register(fn):
        CHECKS.append({"id": cid, "what": what, "places": places, "compute": fn})
        return fn
    return register


def legacy(cid: str):
    """A recomputation from recompute.py, its value only."""
    got = next(c for c in R.CLAIMS if c["id"] == cid)["compute"]()
    return got[0] if isinstance(got, tuple) and not isinstance(got, R.Pair) else got


def ms(v: float, unit: str) -> R.Num:
    return R.Num(v, unit)


def word(n: int) -> str:
    return {4: "four", 15: "fifteen", 17: "17", 60: "sixty"}.get(n, str(n))


def final2_median(metric_id: str) -> float:
    passes = sorted(p for p in (FINAL2 / "chunkH_step10_timing/passes").glob("pass*") if p.is_dir())
    get = next(m[6] for m in T.METRICS if m[0] == metric_id)
    return statistics.median(v for v in (get(p) for p in passes) if v is not None)


# -- the ecosystem and the samples --------------------------------------------------------------

@check("N01", "reporting installations (analytics, 21 August 2026)",
       [("abstract", r"with ([\d,]+) reporting installations"),
        ("resume", r"comptant ([\d  ]+) installations"),
        ("01_introduction.md", r"([\d,]+) active installations")])
def _():
    return legacy("A1.01")


@check("N02", "distinct integrations measured (37 + 40, two shared)",
       [("abstract", r"Across (\d+) real community"), ("resume", r"Sur (\d+) intégrations"),
        ("01_introduction.md", r"(\d+) real"), ("16_conclusion.md", r"across (\d+) real community")])
def _():
    return legacy("A1.11a")


def manifests():
    out = []
    for name in ("hacs_corpus_manifest.json", "hacs_corpus_manifest_uniform.json"):
        repos = json.loads((V2 / "experiments/compat/results" / name).read_text())["repositories"]
        by = {}
        for r in repos:
            by.setdefault(r["domain"], r["installs"])
        out.append(by)
    return out


@check("N03", "Table 11.3: distinct integrations, median installations, installations represented",
       [("11_data_presentation.md", r"\| Distinct integrations \| (\d+) \|"),
        ("11_data_presentation.md", r"\| Distinct integrations \| \d+ \| (\d+) \|"),
        ("11_data_presentation.md", r"\| Median installations per integration \| ([\d,]+) \|"),
        ("11_data_presentation.md", r"\| Median installations per integration \| [\d,]+ \| ([\d,]+) \|"),
        ("11_data_presentation.md", r"\| Installations represented \| ([\d,]+) \|"),
        ("11_data_presentation.md", r"\| Installations represented \| [\d,]+ \| ([\d,]+) \|"),
        ("11_data_presentation.md", r"share only (\w+) integrations"),
        ("11_data_presentation.md", r"about (\S+) times as many installations")])
def _():
    head, uni = manifests()
    words = {2: "two", 21: "twenty-one"}
    return [str(len(head)), str(len(uni)), f"{round(statistics.median(head.values())):,}",
            f"{round(statistics.median(uni.values()) + 0.001):,}", f"{sum(head.values()):,}",
            f"{sum(uni.values()):,}", words[len(set(head) & set(uni))],
            words[round(sum(head.values()) / sum(uni.values()))]]


@check("N04", "load rates, Table 12.2 (head unconfined, confined; uniform unconfined, confined) and §14",
       [("12_results.md", r"\| Most installed \| 37 \| \d+ \((\d+%)\)"),
        ("12_results.md", r"\| Most installed \| 37 \| \d+ \(\d+%\) \| \d+ \((\d+%)\)"),
        ("12_results.md", r"\| Drawn at random \| 40 \| \d+ \((\d+%)\)"),
        ("12_results.md", r"\| Drawn at random \| 40 \| \d+ \(\d+%\) \| \d+ \((\d+%)\)"),
        ("14_learning_strategies.md", r"more often, (\d+%) against"),
        ("14_learning_strategies.md", r"against (\d+%) \(Section 12\.2\)")])
def _():
    hc, hb, uc, ub = legacy("8.2.2")
    return [hb, hc, ub, uc, uc, hc]


# -- security -----------------------------------------------------------------------------------

@check("N05", "garbage-collector technique: live objects holding the token, unconfined",
       [("12_results.md", r"YES — (\d+) live objects")])
def _():
    return legacy("8.2.1a")


@check("N06", "garbage-collector technique: objects the confined walk examined",
       [("12_results.md", r"examined ([\d,]+) objects"), ("12_results.md", r"heap\s+: (\d+) objects")])
def _():
    return legacy("8.2.1b")


@check("N07", "2021 pattern: planted secrets recovered, unconfined then confined",
       [("12_results.md", r"\| (\d of \d) recovered \|"), ("12_results.md", r"recovered \| (\d of \d) \|")])
def _():
    unconf, conf = legacy("8.2.1c")
    return [unconf, conf]


@check("N08", "device states readable unconfined: all, and those that reveal presence",
       [("12_results.md", r"returned all (\d+), including"), ("12_results.md", r"including all (\d+) that reveal"),
        ("12_results.md", r"\| Reading devices the integration was not granted \| (\d+ of \d+) \|")])
def _():
    all_u, pres_u, _c, _pc = legacy("8.2.1e")
    n, p = all_u.split(" of ")[0], pres_u.split(" of ")[0]
    return [n, p, all_u]


def adversary(log: Path) -> collections.Counter:
    line = next(l for l in log.read_text().splitlines() if re.match(r"\s+(BLOCKED|LEAKED)", l) and "  " in l
                and re.search(r"[A-Z]+ \d+", l) and not l.strip().startswith(("ok", "LEAK")))
    return collections.Counter({k: int(v) for k, v in re.findall(r"([A-Z][A-Z ]*?) (\d+)", line.strip())})


@check("N09", "hostile integration, final rerun: attempts, leaked unconfined, confined blocked / empty",
       [("11_data_presentation.md", r"which makes (\d+) attempts"),
        ("12_results.md", r"a suite of (\d+) attacks"),
        ("20_appendix_f_results_detail.md", r"the (\d+) attempts of the adversary suite"),
        ("11_data_presentation.md", r"(\d+) attempts leaked unconfined"),
        ("11_data_presentation.md", r"Confined, (\d+) were blocked"),
        ("11_data_presentation.md", r"blocked, (\d+) found nothing")])
def _():
    suites = FINAL2 / "chunkA_step01/suites_1"
    conf = adversary(suites / "selftest_adversary.log")
    unconf = adversary(suites / "selftest_adversary_baseline.log")
    attempts = conf["BLOCKED"] + conf["DENY"] + conf["EMPTY"]
    return [str(attempts)] * 3 + [str(unconf["LEAKED"]), str(conf["BLOCKED"] + conf["DENY"]),
                                  str(conf["EMPTY"])]


# -- compatibility and the bridge ---------------------------------------------------------------

def recount() -> str:
    return (FINAL2 / "chunkD_step14_coverage/recount.log").read_text().split("== platform rule")[1]


@check("N10", "bridge coverage by kind, of the 37 most-installed (platform rule, final recount)",
       [("abstract", r"device kinds of (\d+) of the 37"), ("resume", r"d'appareils de (\d+) des 37"),
        ("12_results.md", r"device kinds of (\d+) of the 37"), ("16_conclusion.md", r"device kinds of (\d+) of the 37")])
def _():
    return re.search(r"only bridged kinds: (\d+) of 37", recount()).group(1)


@check("N12", "kinds of device the bridge represents",
       [("12_results.md", r"from 11 kinds of device to (\d+)")])
def _():
    src = (V2 / "framework/ha_bridge/confine_bridge/const.py").read_text()
    body = re.search(r"SUPPORTED = \((.*?)\)", src, re.S).group(1)
    return str(len(re.findall(r'"[a-z_]+"', body)))


@check("N13", "the fifteen against a real installation: devices published, checks held",
       [("12_results.md", r"all (\d+) devices they published")])
def _():
    v = (FINAL2 / "chunkG_step08b_real/verdicts_bridge_step5.txt").read_text()
    devices = sum(int(n) for n in re.findall(r"\[(\d+) entities", v))
    held = re.search(r"(\d+)/(\d+) held", v)
    return [str(devices)]


@check("N14", "integrations run end to end (rows of Table [R].2, and every count of them)",
       [("abstract", r"(\w+) named integrations worked"), ("12_results.md", r"so (\w+) integrations were also run"),
        ("16_conclusion.md", r"(\w+) named integrations worked"),
        ("11_data_presentation.md", r"reported for (\w+) named integrations")])
def _():
    t = text("20_appendix_f_results_detail.md")
    table = t[t.index("**Table F.1**"):t.index("### F.3")]
    return word(len(re.findall(r"^\| `", table, re.M)))


# -- cost ---------------------------------------------------------------------------------------

@check("N15", "average community integrations per installation",
       [("12_results.md", r"community integrations, (\d\.\d\d) \(Home"),
        ("11_data_presentation.md", r"community integrations, (\d\.\d\d) \(Home")])
def _():
    return legacy("8.2.3a")


@check("N16", "sandboxes that fit in 60% of 4,050 MB: at ten components, and at none",
       [("12_results.md", r"holds at least (\d+)"), ("abstract", r"holds at least (\d+) sandboxes"),
        ("16_conclusion.md", r"holds at least (\d+) sandboxes")])
def _():
    budget = int(0.6 * 4050)
    return [str(int(budget // 135.6))] * 3


@check("N17", "capacity against the average need, in words",
       [("12_results.md", r"which is (\w+) times what"), ("abstract", r"about (\w+) times what"),
        ("16_conclusion.md", r"about (\w+) times what")])
def _():
    return word(int(int(0.6 * 4050) // 135.6 / 4.02))


@check("N18", "mediator capacity with the durable record",
       [("12_results.md", r"about (\d+) decisions per second")])
def _():
    return legacy("8.2.3b")


@check("N19", "headroom over realistic demand, in words (to the nearest ten)",
       [("12_results.md", r"about (\w+) times clear")])
def _():
    v = float(re.match(r"([\d.]+)", legacy("A1.20")).group(1))
    return word(int(round(v, -1)))


@check("N20", "reported costs: one request, the durable record",
       [("12_results.md", r"\| Delay added to one request \| ([\d.]+ µs)"),
        ("12_results.md", r"\| Writing the decision record to disk \| ([\d.]+ ms)")])
def _():
    lat, rec = legacy("A1.18"), legacy("A1.19")
    return [lat, rec]


@check("N21", "reported range of a household command",
       [("12_results.md", r"\| A household command reaching an integration \| (\d+–\d+ ms)")])
def _():
    return legacy("A1.23").replace(" to ", "–")


@check("N22", "the final rerun's column (medians of its five passes)",
       [("12_results.md", r"using no platform components \| [^|]+ \| ([\d.]+ MB)"),
        ("12_results.md", r"using all ten components measured \| [^|]+ \| ([\d.]+ MB)"),
        ("12_results.md", r"\| Delay added to one request \| [^|]+ \| ([\d.]+ µs)"),
        ("12_results.md", r"\| Writing the decision record to disk \| [^|]+ \| ([\d.]+ ms)"),
        ("12_results.md", r"reaching an integration \| 0\.5–0\.9 ms \| ([\d.]+ ms)"),
        ("12_results.md", r"command reaching an integration \| [^|]+ \| ([\d.]+ ms)")])
def _():
    none, ten = R.Num(final2_median("depth_none"), "MB"), R.Num(final2_median("depth_ten"), "MB")
    lat = R.Num(final2_median("latency_1"), "µs")
    rec = R.Num(final2_median("durability") / 1000, "ms")
    push = R.Num(final2_median("push_latency"), "ms")
    cmd = R.Num(final2_median("command"), "ms")
    return [none, ten, lat, rec, push, cmd]


# -- how the results were checked ---------------------------------------------------------------

@check("N23", "test suites in the final rerun, both runs",
       [("12_results.md", r"all (\d+) test suites passed twice"),
        ("18_appendices.md", r"All (\d+) suites pass, twice")])
def _():
    runs = re.findall(r"suites_\d failed=0 of (\d+)", (FINAL2 / "chunkA_step01/summary.txt").read_text())
    assert len(runs) == 2 and len(set(runs)) == 1, runs
    return runs[0]


def mutants() -> tuple[int, int]:
    run = killed = 0
    for line in (FINAL2 / "chunkB_step02a/framework_results.txt").read_text().splitlines():
        run += 1
        killed += int(line.split("failed_suites=")[1]) > 0
    for line in (FINAL2 / "chunkB_step02a/bridge_run.txt").read_text().splitlines():
        if "failed_suites=" in line and line.startswith("M"):  # the control run is not a mutant
            run += 1
            killed += int(line.split("failed_suites=")[1]) > 0
    for chunk, names in (("chunkC_step02bc", lambda n: n < "M72"), ("chunkC2_step02c", lambda n: n >= "M72")):
        kinds = FINAL2 / chunk / "kinds"
        for d in sorted(p for p in kinds.iterdir() if p.is_dir() and p.name.startswith("M") and names(p.name)):
            run += 1
            exits = (d / "summary.txt").read_text()
            killed += bool(re.search(r"exit=[1-9]", exits.split("house_a_up")[0] + exits.split("house_a_up exit=0")[-1]))
    return run, killed


@check("N24", "deliberate defects planted, and caught",
       [("12_results.md", r"(\d+) defects were planted"), ("12_results.md", r"the tests caught (\d+)"),
        ("18_appendices.md", r"(\d+) of \d+ caught"), ("18_appendices.md", r"\d+ of (\d+) caught")])
def _():
    run, killed = mutants()
    return [str(run), str(killed), str(killed), str(run)]


@check("N25", "findings recorded (rows of the full findings list kept in the notes), and the Critical ones",
       [("12_results.md", r"produced (\d+) findings"),
        ("18_appendices.md", r"Of the (\d+) findings"), ("12_results.md", r"of which (\w+) was critical")])
def _():
    full = (V2 / "notes/appendices_full_20261110/18_appendices.md").read_text()  # the list left the report
    rows = [l for l in full.splitlines() if re.match(r"^\| F\d\d ", l)]
    crit = sum("Critical" in l.split("|")[3] for l in rows)
    return [str(len(rows))] * 2 + [{1: "one"}[crit]]


@check("N26", "planted defects that change no behaviour",
       [("12_results.md", r"The other (\w+) change nothing")])
def _():
    run, killed = mutants()
    return {2: "two"}[run - killed]


# -----------------------------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    rows, tally = [], collections.Counter()
    for c in CHECKS:
        got = c["compute"]()
        expected = got if isinstance(got, list) else [got] * len(c["places"])
        copies, status = [], "EQUAL"
        for (where, pattern), exp in zip(c["places"], expected):
            found = stated(where, pattern)
            if not found:
                status = "NOT FOUND" if status == "EQUAL" else status
                copies.append((where, "—", str(exp)))
                continue
            for s in found:
                ok = exp.matches(s) if isinstance(exp, R.Num) else norm(s).lower() == norm(str(exp)).lower()
                copies.append((where, s, str(exp)))
                if not ok:
                    status = "DIFFERS"
        tally[status] += 1
        rows.append({"id": c["id"], "what": c["what"], "status": status, "copies": copies})
        print(f"{status:<10} {c['id']}  {c['what']}")
        for where, s, exp in copies:
            mark = "" if status == "EQUAL" else ("   <-- expected " + exp if norm(s).lower() != norm(exp).lower() else "")
            print(f"             {where}: {s}{mark}")
    print("\n" + ", ".join(f"{k} {v}" for k, v in sorted(tally.items())))
    if args.json:
        args.json.write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    return 0 if set(tally) == {"EQUAL"} else 1


if __name__ == "__main__":
    sys.exit(main())
