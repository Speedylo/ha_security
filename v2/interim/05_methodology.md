# 5 Methodology

## 5.1 Research design

The project combines an engineering method, which produces the confinement framework, with a quantitative, experimental evaluation of it. The engineering method follows a fixed order. Requirements were written first, each traced to a finding about the problem, and a threat model was written before the design, so that threats were listed independently of the controls that would later answer them. The threat model follows the risk-management process of ISO 31000, in which risks are assessed before they are treated (International Organization for Standardization [ISO], 2018), and classifies threats with the STRIDE categories of spoofing, tampering, repudiation, information disclosure, denial of service and elevation of privilege (Shostack, 2014). It identified nineteen threats, together with seven residual risks that the design accepts and states rather than removes. The design was then chosen against alternatives, implemented and evaluated.

The framework that this method produced has three parts. Each community integration runs in its own Linux sandbox, an isolated environment with its own view of the file system and processes, against a minimal copy of the platform. A separate component, the mediator, carries every action the integration takes on the household's real installation and checks it against the permissions the owner approved. The owner approves those permissions in the platform's own interface, and every decision is written to a log that cannot be altered without detection.

The evaluation is quantitative and uses a paired design. Every security and compatibility result is the difference between two arms run on the same device, with the same platform release and in the same session: in the confined arm the integration runs inside the framework, and in the unconfined arm the same integration runs as Home Assistant runs it today. Confinement is therefore the only variable between the arms. The pairing gives a negative result its meaning, because a security test that finds nothing could simply be broken; if the same attack succeeds unconfined, the test is shown to work, and its failure under confinement can be attributed to the framework.

The evaluation tests one claim: that unmodified community integrations can be confined at a cost worth paying. The claim divides into three assertions that can fail independently, that confinement is effective, compatible and affordable. Following Popper's (1959) criterion that a claim is scientific only if some observation could refute it, each assertion was given a falsifier, a result that would show it false, on 2 September 2026, before any of the measurements it covers had been run (Table 5.1). The same rule applied to every later experiment: its prediction was committed to the project's repository before it ran, and any text later found wrong was corrected by a dated note rather than rewritten.

**Table 5.1**
*The three assertions and what would falsify them*

| Assertion | Falsified if |
|---|---|
| Effective | Either published attack technique succeeds under confinement, or a platform credential can be recovered from inside a sandbox |
| Compatible | The unconfined arm shows that most of the confined failures are caused by the design rather than by the integrations or the platform |
| Affordable | The device cannot hold as many sandboxes as the average installation using the community store has community integrations (4.02), or mediation changes what the platform can do |

## 5.2 Data sources

The study has no human participants. Its data come from software and from measurements on one device, from four sources.

The first source is the community integrations themselves. Two samples were drawn from the Community Store's catalogue (HACS, n.d.), because they answer different questions (Table 5.2). The head-weighted sample, the 40 most-installed repositories, describes what most installations run. The uniform sample, 40 repositories drawn with equal probability using a recorded random seed, describes what most integrations are. The two share only two members, giving 75 distinct integrations, and every integration was used exactly as published.

**Table 5.2**
*The two samples of community integrations*

| | Head-weighted | Uniform |
|---|---|---|
| Selection | The 40 most-installed repositories | 40 repositories drawn at random (seed 20260902) |
| Integrations measured | 37 | 40 |
| Median installations | 16,294 | 48 |
| Installations represented | 998,478 | 46,979 |

The second source is the attacks. The two published attack techniques by a hostile integration were reproduced: the garbage-collector technique by which one integration reaches another's data (Corno & Mannella, 2022), and the path-traversal pattern disclosed in 2021, by which an integration reads files outside its own directory (Home Assistant, 2021a). A further 39 attacks were derived from the project's own threat model and built into a single hostile integration. The third source is Home Assistant's published analytics, which supply the benchmark of 4.02 community integrations per installation (Home Assistant, n.d.-b). The fourth is the test environment, held fixed throughout: a Raspberry Pi 5 with 4 GB of memory, running Raspberry Pi OS (Debian 13) and an unmodified Home Assistant 2026.8.3, with every step run as an ordinary user rather than as the system administrator.

Holding the environment fixed makes the arms comparable, but it also limits how far the results reach. They describe one platform release on one device, and neither sample covers integrations distributed outside the Community Store.

## 5.3 Data collection methods

Data were collected through three kinds of experiment, each run in both arms.

The security experiments ran the attacks from inside a sandbox and recorded one of three outcomes for each attempt: blocked, when something refused it; empty, when it succeeded but found nothing because nothing was there; and leaked, when it returned something it should not. Blocked and empty outcomes are kept apart because a refusal depends on a check that an attacker might evade, whereas an empty result depends on the resource being absent from the sandbox. Two secrets were planted outside the sandbox as canaries, so that any leak could be detected unambiguously.

The compatibility experiments loaded each of the 75 integrations and recorded whether it imported and set up cleanly, confined and unconfined. This is an upper bound on compatibility, because an integration that loads may still fail later. A stronger test, running an integration end to end with its entities and actions working, was possible only for integrations that need no account details: 26 of the 37 head-weighted integrations require an API key, password or similar before they can be configured. Thirteen integrations were run end to end and are reported by name rather than as a rate.

The performance experiments measured memory and delay. Memory was measured as the proportional set size, which divides each memory page among the processes that share it, because most of a sandbox consists of interpreter pages that the operating system shares between sandboxes. Each figure was measured in five passes over frozen code, the first three each after a fresh start of the device, and in five more passes at the final version.

The measuring instruments were themselves tested. The 29 automated test suites were run twice on the device at the final version, and 53 deliberate defects were introduced into the code to check that the suites detect them. A final full rerun of every experiment was made from a fresh copy of the code at the submitted version, with its predictions committed beforehand.

## 5.4 Data analysis methods

The analysis is descriptive, because the experiments compare two arms under controlled conditions rather than sample from a population. Security results are reported attack by attack, as the outcome in each arm. Compatibility results are reported as two numbers that are never combined, the share of integrations that load and the named set that runs end to end, so that the weaker measure cannot be read as the stronger.

Performance figures are summarised by the median across passes and the range of all passes. A figure passes if its median falls within a tolerance fixed before the first pass, 20% for timings and 5% for memory, and a figure outside it is reported as a finding rather than averaged away. The 99th percentile is recorded for each pass to show the worst cases. A bootstrap confidence interval of the median was also computed (Efron, 1979), but with only five passes it adds little beyond their range, so the range is what is reported.

Three further rules govern how results are presented. No single score of "threats controlled" is reported, because it would merge attacks that were refused, attacks that found nothing and risks accepted by decision. Where a population is small, results are given as named cases. And the strength of each statement follows its evidence: a verified result is said to show, a qualified one to suggest, and an argued one is presented as argument.

## 5.5 Ethical considerations

The project collected no personal data about anyone other than the author. Every measurement ran on the author's own device and test installation, so no household's data were observed. Six integrations contacted live online services at their normal rates, four of them public services needing no account and two through free accounts the author created for the purpose, and two integrations that control devices on the home network were tested against simulated devices rather than real ones.

The security work was designed so that no third party was harmed. The attacks were reproduced with integrations written for the evaluation, not against the vulnerable versions of real integrations, so no one else's software or users were attacked. One weakness found by code review, an escape through a shared terminal, was described and fixed but deliberately not developed into a working exploit.

Credentials needed for testing, including the platform access token held by the mediator, were kept on the device with owner-only permissions. They were never placed in a conversation with the AI tool, and the project's code was scanned for them before each upload to its repository. A final consideration concerns independence: the framework and the attacks used to evaluate it were built by the same AI-assisted process, so the security results rest on the project's own attacks rather than on an independent test, a limit that Section 6.4 discusses.
