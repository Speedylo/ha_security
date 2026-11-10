# 11. Data Presentation

This section describes the data on which Section 12 rests. It covers the three questions the evaluation asked, with the answer that would count as "no", the device and the two ways each integration was run, the two samples of integrations, and what was recorded for each.

## 11.1 The three questions

The project claims that existing integrations can be confined, without changing them, at a cost worth paying. The claim holds only if three assertions hold: confinement protects the household (A), integrations still work when confined (B), and a home device can afford it (C). A sandbox that blocked every attack but broke most integrations would satisfy the first assertion and still defeat the claim, so all three were tested. Following Popper's (1959) criterion that a claim is open to test only if some observation could refute it, each assertion was given the result that would show it false. These conditions were written on 2 September 2026, before any of the measurements they describe, and are set out in Table 11.1.

**Table 11.1**
*The three assertions and what would show them false*

| Assertion | Shown false if |
|---|---|
| A. Confinement protects the household | From inside a sandbox, the garbage-collector technique (Corno & Mannella, 2022) reaches a platform object, a planted credential is recovered, or the 2021 file-theft pattern (Home Assistant, 2021a) succeeds |
| B. Integrations still work | The unconfined run loads almost all of the most-installed integrations and the confined run does not, so that most of the shortfall comes from the design |
| C. A home device can afford it | The reference device cannot hold as many sandboxes as the average installation has community integrations, 4.02 (Home Assistant, n.d.-c), or mediation changes what the platform can do |

Each condition names an observation rather than a level of satisfaction. The budget in C is stated against an average because the platform publishes no spread across installations, a weakness that Section 12.5 carries into the result. One further condition applies to the evaluation itself, which fails if it reports as passed a requirement it cannot show; Appendix [R].6 describes how this was checked.

## 11.2 The device and the two runs

Every measurement was taken on one device, the reference hardware that requirement C4 names. Table 11.2 records its configuration.

**Table 11.2**
*The test environment*

| Item | Value |
|---|---|
| Device | Raspberry Pi 5, 4 GB of memory |
| Operating system | Raspberry Pi OS (Debian 13), kernel 6.12.47, 64-bit Arm |
| Platform | Home Assistant 2026.8.3, unchanged, on Python 3.14.7 |
| Framework | Python 3.13.5, standard library only |
| Privileges | An ordinary user; no step needs administrator rights |

Every security and compatibility test was run twice on this device, with the same release and in the same session. In the confined run the integration runs inside the framework, and in the unconfined run it runs as Home Assistant runs it today, so confinement is the only difference between the two. The pairing is what gives a negative result its meaning. A security test that finds nothing is ambiguous, because a broken test also finds nothing, but the same attack succeeding unconfined shows that the test works, so its failure when confined can be attributed to the framework. The unconfined run was also made generous: it sets up every component and package the integration declares, so that a failure is charged to confinement rather than to a weak comparison.

## 11.3 The two samples

Compatibility was measured on real, unmodified integrations from the Home Assistant Community Store (HACS, n.d.), using two samples that answer different questions. Table 11.3 compares them.

**Table 11.3**
*The two samples of community integrations*

| | Most installed | Random |
|---|---|---|
| Selection | The 40 most-installed catalogue entries | 40 entries drawn with equal probability (seed 20260902) |
| Distinct integrations | 37 | 40 |
| Median installations per integration | 16,294 | 48 |
| Installations represented | 998,478 | 46,979 |

The first sample describes what most installations run, and the second describes what most integrations are. The 40 entries of the first sample yield 37 integrations because the platform's analytics count installations by integration name, and three names belong to two repositories each. The two samples share only two integrations, so the second is close to an independent sample of the same catalogue, while the first represents about twenty-one times as many installations. Neither covers integrations distributed outside the catalogue.

## 11.4 What was recorded

Security was recorded by a hostile integration written for the evaluation, which makes 39 attempts from inside a sandbox, together with one permitted request for the device it declared. Each attempt ends in one of three outcomes. It is blocked when it fails with an error, empty when it succeeds but finds nothing, and leaked when it returns something it should not. Blocked and empty outcomes are kept apart because they fail for different reasons: a blocked attempt meets a check or a missing file, while an empty one finds that the resource is not there to take. Table 11.4 shows five attempts from the final rerun.

**Table 11.4**
*Five attempts by the hostile integration, final rerun of 1 November 2026*

| Attempt | Unconfined | Confined |
|---|---|---|
| Read the household's secrets file through a relative path | Leaked: the planted secret | Blocked: no such file |
| Connect to a service running on the device | Leaked: connected | Blocked: connection refused |
| Create an isolated environment of its own, a step towards escape | Leaked: succeeded | Blocked: not permitted |
| List the files in the device owner's home directory | Leaked: the file names | Empty: nothing to list |
| Read a device it did not declare | No check: the code acts directly | Blocked: refused by the mediator |

Across the whole suite, 11 attempts leaked unconfined. Confined, 29 were blocked, 10 found nothing and none leaked.

Compatibility is recorded as two numbers that are never combined. The first, whether an integration loads and sets up cleanly, was measured for every integration in both samples. It is an upper bound, because an integration that loads may still fail when it first fetches data. The second is whether an integration works end to end, with its devices and actions behaving as they do unconfined. Most integrations cannot be tested this way, because they need an account key, a password or a device address before their setup can complete, so end-to-end results are reported for fifteen named integrations rather than as a rate.

Cost is recorded as memory and time. Memory is counted as proportional set size, which divides each page a process holds by the number of processes that share it (Linux kernel documentation, n.d.), because most of a sandbox consists of pages the kernel shares between sandboxes. Each figure was measured in ten passes on fixed code and in five more in the final rerun, and the median across passes is the figure reported.

Section 12 presents these data under three rules. No single figure of threats controlled is given, because it would merge blocked attempts, empty ones and risks retained by decision. Where a sample is small, the integrations are named with their outcomes, so that a reader can see which cases a figure rests on. Each statement is also as strong as its evidence: a measured result is said to show, a narrower one to suggest, and an argued one is presented as argument.
