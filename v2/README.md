# Confining unmodified third-party integrations in Home Assistant

This directory is the capstone project: *Confining Unmodified Third-Party Integrations in Home
Assistant — A Declared-Authority Architecture and Its Measured Cost*. Everything outside `v2/` in this
repository is the earlier feasibility spike, which is prior work and is not imported here.

Every community integration runs inside Home Assistant's own process with all of its authority. This
project runs each one, unmodified, in its own sandbox on the Raspberry Pi the platform usually lives
on. Anything the integration does outside its sandbox goes through a mediator. The mediator decides
each request against what the integration declared in its manifest, records the decision durably
before acting on it, and then acts on the house's real Home Assistant.

## Where to start

| If you want | Read |
|---|---|
| The argument and the results | `report/`, from `00_front_matter.md` (abstract and contents) to `08_conclusions.md` |
| To reproduce the results | `REPRODUCE.md`: the environment from a blank Pi, then every suite |
| One experiment's command and its raw results | `experiments/<name>/README.md`; `REPRODUCE.md` §11 maps each to its report section |
| The code | `framework/README.md`; the modules follow Chapter 6's sections |
| How every claim was checked before submission | §7.45, `notes/verification_plan_20261005.md` and `verify/claims_register.md` |
| A plain-language overview | `PROJECT_OVERVIEW.md` (dated 2026-09-06; its notes at the top say what has changed) |
| Where the work stands today | the top of `STATE.md` |

## Layout

| Directory | What it holds |
|---|---|
| `report/` | the report, one file per chapter; `toc.py --check` verifies the contents page and its counts |
| `framework/confine/` | the framework: sandbox, mediator, manifest, audit log, and the 27 self-test suites |
| `framework/ha_bridge/` | the bridge integration installed in the house's Home Assistant |
| `experiments/` | one directory per measurement: its script, README and committed results |
| `figures/` | figure sources, the corpus fetcher and the API-surface measurement |
| `verify/` | the verification campaign's scripts and claim register |
| `notes/` | working notes, including each experiment's predictions, committed before it ran |
| `submission/` | the draft in the programme's template, *stale until phase R* |
| `proposal/` | the programme proposal |

**Conventions worth knowing before reading the report.** Predictions are committed before the
measurement they predict, and are never revised. A section that later turns out to be wrong keeps its
text and gains a dated pointer to the correction, so the record of what was believed, and when, is
part of the result (§8.4).
