# Confining Unmodified Community Integrations in Home Assistant

Every community integration runs inside Home Assistant's own process with all of the platform's authority. This project runs each one, unmodified, in its own sandbox on the Raspberry Pi the platform usually lives on. Anything the integration does outside its sandbox goes through a mediator, which decides each request against what the integration declared in its manifest, records the decision durably before acting on it, and then acts on the house's real Home Assistant.

## Where to start

| If you want | Read |
|---|---|
| The final report | `submission/`: its source, one Markdown file per section, and the script that builds it |
| To reproduce the results | `REPRODUCE.md`: the environment from a blank Raspberry Pi, then every suite and experiment |
| One experiment's command and raw results | `experiments/<name>/README.md` |
| The code | `framework/README.md` |
| How every claim was checked | `verify/claims_register.md` and `notes/verification_plan_20261005.md` |
| How AI assistance was used and checked | The log of every correction to AI output, `notes/ai_use_log.md` |

## Layout

| Directory | What it holds |
|---|---|
| `framework/confine/` | The framework: sandbox, mediator, manifest, audit log, and the self-test suites |
| `framework/ha_bridge/` | The bridge integration installed in the house's own Home Assistant |
| `experiments/` | One directory per measurement: its script, README and committed results |
| `figures/` | Figure sources, the corpus fetcher and the platform-interface measurement |
| `verify/` | The verification campaign's scripts and claim register |
| `notes/` | Each experiment's predictions, committed before it ran, and the project's working notes |
| `submission/` | The final report's source and build script |
| `interim/` | Only `build_interim.py`, the template handling the final report's build reuses (the interim report itself is submitted separately) |

The final report's source is here; the built PDF, the interim report and the diaries are submitted to the programme separately.

**Section numbers.** References such as §7.17 or "Chapter 6" in `REPRODUCE.md`, the READMEs, `notes/` and the code's docstrings point to the project's working report, which is kept locally and not published. The final report in `submission/` presents the same work: the framework in Section 9, the evaluation in Sections 11 and 12, and the detail in its appendices.

## Conventions

Predictions are committed before the measurement they predict and are never revised. A statement that later turns out to be wrong keeps its text and gains a dated pointer to the correction, so the record of what was believed, and when, is part of the result.
