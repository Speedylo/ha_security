# Confining Unmodified Community Integrations in Home Assistant

Capstone project, School of Science and Engineering, Al Akhawayn University (Fall 2026).

Home Assistant runs every community integration inside its own process, with the platform's full authority. This project confines each integration, unmodified, in its own Linux sandbox. Everything it does outside the sandbox passes through a mediator, which checks the request against the permissions a person approved and records the decision before acting. The framework was evaluated on a Raspberry Pi 5 against the same integrations run without confinement.

Everything is in [`v2/`](v2/README.md): the framework, the experiments and their results, the verification, and the reports.
