# Confining Unmodified Community Integrations in Home Assistant

Every community integration runs inside Home Assistant's own process with all of the platform's authority. This project runs each one, unmodified, in its own sandbox on the Raspberry Pi the platform usually lives on. Anything the integration does outside its sandbox goes through a mediator, which decides each request against what the integration declared in its manifest, records the decision durably before acting on it, and then acts on the house's real Home Assistant.

## Where to start

| If you want | Read |
|---|---|
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
| `report/` | The working report against which every claim was registered and checked; the verification scripts read it |
| `proposal/` | The project proposal |

The reports and diaries are submitted to the programme separately; this repository holds the work they describe.

## Conventions

Predictions are committed before the measurement they predict and are never revised. A statement that later turns out to be wrong keeps its text and gains a dated pointer to the correction, so the record of what was believed, and when, is part of the result.
