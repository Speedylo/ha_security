# Confining Unmodified Community Integrations in Home Assistant

Every community integration runs inside Home Assistant's own process with all of the platform's authority. This project runs each one, unmodified, in its own sandbox on the Raspberry Pi the platform usually lives on. Anything the integration does outside its sandbox goes through a mediator, which decides each request against what the integration declared in its manifest, records the decision durably before acting on it, and then acts on the house's real Home Assistant.

## Where to start

| If you want | Read |
|---|---|
| The final report | `submission/Younes_Rahati_Final_Report.pdf` |
| To reproduce the results | `REPRODUCE.md`: the environment from a blank Raspberry Pi, then every suite and experiment |
| One experiment's command and raw results | `experiments/<name>/README.md` |
| The code | `framework/README.md` |

## Layout

| Directory | What it holds |
|---|---|
| `framework/confine/` | The framework: sandbox, mediator, manifest, audit log, and the self-test suites |
| `framework/ha_bridge/` | The bridge integration installed in the house's own Home Assistant |
| `experiments/` | One directory per measurement: its script, README and committed results |
| `figures/` | Figure sources, the corpus fetcher and the platform-interface measurement |

The final report is published here as a PDF (`submission/`); its sources, the interim report and the diaries are submitted to the programme separately.

**References to unpublished material.** Section numbers such as §7.17 or "Chapter 6" in `REPRODUCE.md`, the READMEs and the code's docstrings point to the project's working report, and paths under `notes/` and `verify/` to its working notes, predictions and verification scripts. All three are kept locally and not published. The final report (`submission/Younes_Rahati_Final_Report.pdf`) presents the same work: the framework in Section 9, the evaluation in Sections 11 and 12, and the detail in its appendices.

## Conventions

Each measurement's prediction was committed before it ran and never revised; the predictions are kept with the working notes. A statement in these READMEs that later turned out to be wrong keeps its text and gains a dated pointer to the correction, so the record of what was believed, and when, is part of the result.
