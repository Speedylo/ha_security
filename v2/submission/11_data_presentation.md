# 11. Data Presentation

This section states what was measured, on what, with which instruments, and how the results are to be read, before Section 12 reports what the measurements showed. An evaluation that introduces its method alongside its results invites the reading that the method was chosen to fit them. The assertions and their falsifiers below were written on 2 September 2026, before any of the measurements they specify had been run, and were not revised in light of the results. The method begins with the claim it tests.

## 11.1 The claim and what would falsify it

The central claim of this project is that unmodified, pre-existing integrations can be confined at a cost worth paying. The claim contains three assertions that can fail independently: confinement is effective, it is compatible, and it is affordable. A sandbox that blocks every attack but breaks most integrations would satisfy the first while defeating the claim, so all three must be tested. Following Popper's criterion of falsifiability [43], each assertion was given a falsifier before measurement: an observation that would show it false, judged where necessary against an unconfined arm in which the same integration runs without the framework. Table 11.1 sets them out.

**Table 11.1 — The three assertions and their falsifiers, fixed on 2 September 2026**

| Assertion | Falsified if |
|---|---|
| A. Confinement is effective | The garbage-collector technique [5] reaches a platform object from inside the sandbox, or a platform credential is recoverable from the sandbox, or the attack pattern disclosed in 2021 [7] succeeds under the framework |
| B. Confinement is compatible | The unconfined arm shows that most of the confined shortfall is caused by the design, that is, the unconfined arm passes substantially all of the head-weighted corpus while the confined arm does not |
| C. Confinement is affordable | The cost of each sandbox reduces the number the reference device can hold below the mean number of community integrations an installation running HACS has, 4.02 [1], or mediation at realistic numbers of sandboxes changes what the platform can do |

Each falsifier names an observation rather than a threshold of satisfaction. Any one condition under A would defeat the architecture, not merely its implementation, because each is an attack the architecture was designed to remove. The falsifier for C is stated against a mean because the platform's telemetry publishes no spread across installations [1], so a budget above the mean may still fail installations in the tail, and this weakness is carried into the result.

A fourth falsifier applies to the evaluation rather than to the framework. The evaluation fails on its own terms if it reports as passed a requirement it cannot demonstrate, or reports an aggregate figure that conceals a breakdown it holds. This condition makes the honesty of the reporting something that can be checked, and Section 12.4 checks it. Assertion B, however, can be tested only against a baseline, which is the subject of the paired design.

## 11.2 The paired design

Every security and compatibility result is the difference between two arms run on the same host, with the same platform release and in the same session. In the confined arm the integration runs inside the framework. In the unconfined arm the same integration runs as Home Assistant runs it today, in a full installation with no namespaces, no system-call filter, no resource limits, no separate file-system view, no mediator and no bridge. Confinement is therefore the only variable between the arms.

The pairing is what gives a negative result its meaning. A security test that finds nothing is ambiguous, because a broken test also finds nothing; the same attack succeeding in the unconfined arm shows that the test works on this host and release, so its failure in the confined arm can be attributed to confinement. The pairing also cuts against the framework. An attack that fails in both arms, for a reason unrelated to confinement, is excluded from the framework's results rather than counted in its favour.

Two decisions in the construction of the arms protect the comparison. Both arms call the same measurement function with the same arguments, so they classify outcomes by the same rules. The unconfined arm is also deliberately generous: it sets up the platform's default components together with every component and package the integration declares, which makes any cost charged to confinement larger rather than smaller. Its first version was less generous, and an integration that declares the `mqtt` component failed unconfined while passing confined; a baseline weaker than the arm it is compared against inverts the cost it is meant to measure. The arms also share one environment, described next.

## 11.3 Environment and corpora

Every measurement was taken on one device, the reference hardware that requirement C4 names, and Table 11.2 records its configuration.

**Table 11.2 — The test environment**

| Item | Value |
|---|---|
| Device | Raspberry Pi 5, 4 GB |
| Operating system | Raspberry Pi OS (Debian 13), kernel 6.12.47, 64-bit Arm |
| Platform | Home Assistant 2026.8.3, unmodified, on Python 3.14.7 |
| Framework | Supervisor and mediator on the operating system's Python 3.13.5, standard library only |
| Privilege | An ordinary user throughout; no step of any run requires root |

Holding the environment fixed makes the arms comparable, but it also limits how far the results generalise: they describe one platform release on one device and one processor architecture. Releases remove interfaces that integrations depend on, and one integration in the head-weighted corpus fails on a constant removed in this very release, so a compatibility figure should be expected to change with the release.

Compatibility was measured on real, unmodified integrations from HACS, the community catalogue [6], and two corpora were used because they answer different questions. Table 11.3 compares them.

**Table 11.3 — The two corpora**

| | Head-weighted | Uniform |
|---|---|---|
| Selection | The 40 most-installed repositories | 40 repositories drawn with equal probability (seed 20260902) |
| Integrations measured | 37 | 40 |
| Install count, median | 16,294 | 48 |
| Installations represented | 998,478 | 46,979 |
| Integrations declaring no platform components | 18 of 37 | 26 of 40 |

The head-weighted corpus describes what most installations run, and the uniform corpus describes what most integrations are. The two share only two members, so the second is close to an independent sample of the same ecosystem rather than a different view of the first, while the first represents twenty-one times the installations of the second. Neither corpus generalises to integrations distributed outside HACS. The instruments applied to these corpora are described next.

## 11.4 Instruments and statistics

Compatibility is reported as two numbers that are never combined. The first, whether an integration imports and sets up cleanly, was measured for every integration in both corpora; it is an upper bound, because an integration that imports may still fail at its first poll. The second is whether an integration was executed end to end, its entities and actions working in a live platform. Most integrations cannot be tested this way: 26 of the 37 head-weighted integrations require an API key, token, password, user name, host or e-mail address before their configuration can complete, and no test of any sandbox can supply those details. End-to-end results are therefore reported as a named set of integrations rather than as a rate.

Security is measured with an adversarial integration that makes 39 attack attempts from inside a sandbox, together with one permitted request for the entity it declared as a control, and records one of three outcomes for each attempt. An attempt is blocked when something refuses it, empty when it succeeds and finds nothing because nothing is there, and leaked when it returns something it should not. The first two are kept apart because a refusal depends on a check that an attacker might evade, while an empty result depends on the resource being absent from the sandbox.

Performance is measured as memory and time. Memory is the proportional set size, which counts each page a process holds divided by the number of processes sharing it [55], because most of a sandbox consists of interpreter pages the kernel shares between sandboxes. Each figure was measured during development and re-measured in five passes over frozen code, the first three each on a separate boot, and in five more passes at the submitted version. A figure passes if the median across passes falls within a tolerance fixed before the first pass, 20% for timings and 5% for memory; a figure outside it is reported as a finding, not averaged away. The 99th percentile is recorded for each pass. A bootstrap 95% interval of the median [56] was computed as well, but resampling five values yields little more than their range, so Section 12 reports the range itself rather than imply a precision five passes cannot give. These instruments produce the data; the rules for presenting it follow.

## 11.5 How the results are presented

Three rules govern how Section 12 presents the data. First, no aggregate figure of threats controlled is reported. Such a figure would merge attacks refused by a check, attacks that found nothing to reach and risks retained by decision into one number, which is the concealment the fourth falsifier names. Section 12 reports each category separately, and Appendix C gives the full register. Second, where the population is small, results are reported as named integrations with their outcomes, so that a reader can see which cases a figure rests on. Third, the strength of each statement follows its evidence: a verified result is said to show, a qualified one to suggest, and an argued one is presented as argument. Under these rules, Section 12 reports each assertion against its falsifier and states whether the falsifier was met.
