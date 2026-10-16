# 6. Logic Model Framework

This section traces the project from the people it serves, through what it assumed and used, to what it produced and what that may change.

## 6.1 Target population

The primary population is the households that run community integrations: 379,326 of Home Assistant's 669,743 active installations, or 56.6%, run the community store, each with a mean of 4.02 community integrations [1]. These households own the assets at risk and carry that risk without a means of acting on it. The second population is the authors, whose 4,220 integrations have a median of 20 installations [1]. Most are volunteers, which is why requirement C1 leaves their code unmodified. What the framework asks of them is smaller: a `permissions` block in the manifest each integration already ships, which no integration carries yet, so every manifest in this evaluation was written by hand. The third is the Home Assistant project, which would have to own any lasting fix.

## 6.2 Underlying assumptions

The project's assumptions are on record, because each was written down as a prediction and committed to the repository before the measurement that could prove it wrong. Table 6.1 scores every prediction that can be counted individually. Nine further notes set pass-or-fail criteria for fixes and checks rather than predicting outcomes, and they are not counted.

**Table 6.1 — Registered predictions, scored**

| Period | Prediction notes | Held | Registered |
|---|---|---|---|
| First evaluation, 2–3 September 2026 | The evaluation plan and 1 note | 2 | 8 |
| Completing and re-measuring the framework, 3–5 October | 16 | 107 | 119 |
| Verification campaign, 7–13 October | 10 | 96 | 102 |
| Final rerun, 16 October | 2 | 14 | 18 |
| **Total** | | **219** | **247** |

The first evaluation is the most informative row, because its predictions were made before the project knew how the ecosystem behaved. The two that held concerned the framework itself: that confining an integration would cost little or no compatibility, and that this result would repeat on a second, independently drawn sample. The six that failed concerned the world around the framework. The least-installed integrations, for example, were expected to load successfully less often than the most popular ones because they are less maintained, and they loaded more often.

Later predictions held far more often, but mainly because most were written about code that had just been read or built, so their rate reflects familiarity rather than foresight. Their 22 misses came largely from the platform's behaviour and from the project's own test tools, and a few exposed limits at the framework's edges, such as a safeguard against an integration that floods the mediator with requests, which also stopped a legitimate performance test. None of the 28 misses concerned the framework's central properties: that integrations are isolated, that they work as well confined as unconfined, and that whatever they did not declare is refused.

Two assumptions could not be tested and are stated as limits: that the kernel's namespaces and system-call filter are sound, and that the person approving a declaration understands it, which no user study examined.

## 6.3 Resources and challenges

### 6.3.1 Resources

The project used one device, one pinned platform release and public data. The device is a Raspberry Pi 5 with 4 GB of memory, the kind of single-board computer on which households run the platform [24], and every reported measurement was taken on it without administrator rights. Home Assistant 2026.8.3 was pinned so that each compatibility figure can be reproduced, and the corpora come from the community store's index. The supervisor and mediator use only Python's standard library, because a confinement tool that brings its own dependencies enlarges the surface it exists to reduce. The code was written with AI assistance, which shortened the building.

### 6.3.2 Challenges

Four challenges shaped the work. Neither the integrations nor the platform could be changed, so confinement is imposed from outside, by a supervisor that builds each sandbox and a mediator that acts on the platform as an ordinary user. The platform moves, and because the framework depends on internals such as the HTTP client helper [22], its results describe only the release measured. The ecosystem limited the evidence: 26 of the 37 most-installed integrations need an account or a device address before their setup can finish, so end-to-end execution reached a named set of thirteen rather than a sample, a ceiling the unconfined arm meets equally. Finally, the project tested its own work, and the code review that found a sandbox escape missed by every suite (F34) shows what the absence of an independent adversary costs.

## 6.4 Activities

The activities followed the order of the method: requirements traced to findings, a threat model written before the architecture, which is how it produced the resource bound S9, an architecture chosen against alternatives, and an implementation with its suites and an adversary to attack it. Evaluation compared every security and compatibility result with an unconfined arm, and a verification campaign then tested the evidence itself, through mutants, fault injection, a code review and a register of claims, until the engineering cut-off on 8 October 2026.

## 6.5 Outputs

The outputs are the eight deliverables of Table 3.3, and each can be run or checked by someone other than the author. The framework and its interface integration run on the reference device, the 29 suites and 53 mutants show what the tests detect, the two corpora and their harness reproduce every compatibility figure, and the record of 153 claims and 63 findings links each claim in this report to its evidence.

## 6.6 Outcomes

### 6.6.1 Short-term outcomes

The short-term outcomes are achieved and measured. The heap-walk attack [5] and the 2021 path-traversal pattern [7] succeed unconfined and find nothing confined. Confinement costs no import-level compatibility across 75 integrations, thirteen integrations run confined end to end, and the reference device holds 17 to 43 sandboxes against a mean of 4.02 integrations per installation [1].

### 6.6.2 Intermediate outcomes

The intermediate outcomes are plausible but not yet shown, and each has a known obstacle. Integrations beyond the evaluation would need manifests, added by their authors or supplied with an installation. The framework would also have to run a household's integrations for months, disk and network bandwidth would need a bound the device does not delegate to an unprivileged user (T16), and an independent adversary would have to attack it. None needs a new research result.

### 6.6.3 Long-term outcomes

The long-term outcome lies with the platform. Because a check inside the platform's process can be reached by the code it restricts [5], a lasting fix would require Home Assistant to place community integrations behind a process boundary itself, and to make its existing per-entity user policy configurable, so that the mediator's own credential could be narrowed (R3). The project cannot deliver that change, but it supplies the evidence a proposal would need: what confinement costs, what a declaration must express, and which threats it closes and which it leaves open.
