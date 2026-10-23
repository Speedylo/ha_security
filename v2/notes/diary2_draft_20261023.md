# Diary 2 — draft for review (2026-10-23, due Sunday 2026-10-25)

> **2026-10-23 11:20: `Diary2.docx` is now the source of truth.** Younes edited it in Word, and this draft does not include his edits. Make further changes in the docx.

Template: `Diary2_Research_Based.docx` (Diary 1 was ticked research-based). The text is first person, as in
Diary 1. **[Younes: …]** marks what only Younes can write. Once this text is approved it goes into the
template unchanged.

---

## Student & Project Details

- Student Name: Younes Rahati
- Project Title: Confining Unmodified Community Integrations in Home Assistant: A Declared-Authority Architecture and Its Measured Cost
- Supervisor: Dr. Fiaz Ahmad
- Report Period: Oct 10 – Oct 25
- Semester: Fall 2026 · Diary No.: 2

## Summary of Supervisor Meetings During This Reporting Period

**[Younes: each meeting's date, what was discussed, feedback on the method or the report, decisions made,
and agreed next steps. The course expects a weekly meeting.]**

## Work Done This Period

### 1. Research Overview & Progress

Home Assistant runs community integrations inside its own process with its full authority. This project
confines each unmodified integration in a Linux sandbox, and it reaches the household's installation and
the network only through a mediator that grants what the integration's manifest declares. The expected
contribution is a working framework and a measured answer to whether this confinement costs compatibility
and performance.

Both of Diary 1's actions are complete. First, a sandbox that keeps repeating refused requests is now cut
off after a fixed number of refusals, within 0.81 s, while its neighbours continue to be served. It is never
restarted with more authority. Second, the report has been rewritten against the current results: 15
sections and 7 appendices, about 43,000 words, typeset at 118 pages. I declared an engineering cut-off on 8
October. After it, the only code changes were fixes for defects that the writing exposed.

There were two changes of scope. A person must now approve an integration's declared permissions in Home
Assistant's interface before its sandbox can start, because the review showed that nothing required this
before (finding F57). The title also says "community integrations" instead of "third-party", because
HACS integrations are written by members of the Home Assistant community.

### 2. Research Questions, Hypotheses & Evaluation Criteria

The research question is whether unmodified integrations that already exist can be confined at a cost
worth paying. The claim splits into three assertions, each of which can fail on its own. Their
falsifiers were fixed on 2 September, before any measurement:

- **A, effective:** falsified if a published attack reaches the platform or a credential from inside a sandbox.
- **B, compatible:** falsified if most integrations that fail confined are failed by the design, as shown by an unconfined run of the same integration.
- **C, affordable:** falsified if the device holds fewer sandboxes than the mean number of community integrations per installation (4.02), or if mediation changes what the platform can do.

The measurable criteria from Diary 1 still apply: confinement may add failures for no more than 5% of
each corpus, and the median mediation latency must stay under 1 ms. The results meet all three
assertions:

- The published attacks succeed unconfined and find nothing confined.
- Across 75 integrations, none fails to load confined without also failing unconfined, and 13 run confined end to end.
- The device holds at least 17 sandboxes, and the mediator runs about sixty times clear of realistic demand.

### 3. Literature Review / Related Work

This period I ran a documented, repeatable literature search covering December 2024 to October 2026. It
searched OpenAlex, Semantic Scholar, arXiv and Google Scholar, and followed forward citations of the
project's four key sources. The search found 758 records, which came to 642 after removing duplicates. Of
these, 590 were excluded on their titles as not about third-party code on a smart-home hub, and the remaining
52 were screened on their abstracts: none closes the gap, and one is adjacent to it.

Tracing citations back from one excluded paper found SandTrap [2]. SandTrap confines JavaScript apps on
trigger-action platforms such as Node-RED and IFTTT, and it is the closest prior work in mechanism.
The gap therefore stands: no published work confines Home Assistant's integrations or measures what
confining them costs. The threat model of Corno and Mannella [1] remains the external model my own threat
register is compared against.

Two further sources shaped the method. Popper's criterion of falsifiability [3] is why each assertion has
a falsifier fixed in advance. The mutation-testing literature [4] is why every security check was deliberately broken, to show
that the test suites catch it.

### 4. Research Methodology & Framework

The method is quantitative and experimental, within an engineering-research workflow. Requirements trace
to evidence, the threat model is written before the design (in ISO 31000's order [5]), and the evaluation
is paired. In the pairing, every integration runs twice on the same device, release and session: once
confined and once unconfined, as Home Assistant runs it today. Confinement is then the only variable.

The pairing is what gives a negative result meaning. An attack that finds nothing confined counts only
if the same attack succeeds unconfined, because otherwise a broken test cannot be told apart from a
working sandbox. Each prediction is committed to the repository before its measurement, and a
prediction later found wrong gets a dated correction instead of a rewrite.

### 5. Experimental / Study Design

All measurements ran on one Raspberry Pi 5 (4 GB), with Home Assistant 2026.8.3 unmodified on Python
3.14.7 and no root at any step. Compatibility used two corpora from HACS, the community catalogue:

- **Head-weighted:** the 40 most-installed repositories, of which 37 were measured. It represents what most installations run.
- **Uniform:** 40 repositories drawn at random with a fixed seed. It represents what most integrations are.

The independent variable is confinement. The dependent variables are:

- each attack's outcome: blocked, empty or leaked;
- whether an integration loads and sets up;
- whether it works end to end;
- latency;
- memory per sandbox.

The unconfined arm is deliberately generous: it loads every component an integration declares, so that
any cost charged to confinement is larger, not smaller. This period I ran the final rerun. It repeated
every measurement, mutant, suite and fault from a fresh clone at the final tag, in 13 steps, each against
a prediction committed beforehand.

### 6. Data Collection & Analysis Plan

Harness scripts write every raw result to files committed in the repository, and both arms classify
outcomes with the same function. Compatibility is reported as two numbers that are never combined: one
for loading and one for working end to end. End-to-end results are a named list of integrations, not a
rate, because most integrations need an account the tests cannot supply.

Timings and memory are medians, taken over five passes on frozen code and five more at the final
version. Each figure has a tolerance fixed in advance: 20% for time and 5% for memory. A figure outside
its tolerance is reported as a finding, not averaged away. The report gives the range across passes
instead of a bootstrap interval, because five values resampled give little more than their range.

### 7. Validation, Reliability & Research Ethics

The claims are validated in five ways:

- **Claim register:** 153 claims, each with its evidence and a pass criterion. 119 are verified, 27 qualified, five argued and two withdrawn.
- **Prediction notes:** a script checks that all 38 notes were committed before their first result.
- **Mutation testing:** 53 hand-written mutants each break one security check. 52 were caught by the suites; the remaining one behaves identically to the original code.
- **Fault injection:** nine injected faults, plus 29 self-test suites.
- **Number check:** every number in the report was checked against the final rerun.

One limit is stated in the report: no independent adversary attacked the framework. An adversary was
planned and dropped, because the framework was built with AI assistance, so neither the AI nor I would
have been independent of the assumptions behind it.

The study has no human participants. Integrations are used under their own licences and not
redistributed. API keys and tokens stay on the Pi with owner-only permissions, and an exact-value
credential scan runs before every push to GitHub (0 hits).

### 8. Progress, Decisions & Challenges

Work completed:

- **End-to-end retest (9 Oct):** 42 of 45 checks held. It found F54: a confined service call lost a list of target devices, and its audit record named no target. I decided to fix it rather than state it as a limitation.
- **Fixes during the writing (10–11 Oct):** F57, the missing human approval, is now an "Allow and start" action in Home Assistant's Repairs panel, bound to the integration's identity and to the permissions shown to the person. F58: the network check treated a carrier-grade NAT range as public internet, and is fixed.
- **Report (11–16 Oct):** each section was drafted, reviewed and approved by me before the next. The literature search was run and screened.
- **Final rerun (16 Oct):** every criterion was met except two, and both are reported. F61: the fault-injection scripts had never been updated for the new approval step. Only the full rerun could find this, which justifies running one. F62: push latency was 0.50 ms against the stated 0.71 ms, faster than expected and with no cause established, so the report gives a range of 0.5–0.9 ms. That brings the total to 63 findings, all recorded in Appendix F.

Decisions:

- Write the whole report first, then run one full rerun at the final tag, instead of rerunning after every fix.
- Exclude a paper whose full text could not be obtained, even though its abstract was relevant, so that no claim rests on a source I have not read.

Challenges:

- The Pi's disk reached 87%. I archived the run outputs and cleaned the device.
- Google Scholar's result pages were not stable between visits, so the protocol records Scholar as a source that cannot be reproduced.
- One check is still open (F18): following the reproduction instructions on a freshly imaged memory card, which needs a spare card.

## References Consulted

1. F. Corno and L. Mannella, "A threat model for extensible smart home gateways," in *Proc. 7th Int. Conf. Smart and Sustainable Technologies (SpliTech)*, Split/Bol, Croatia, 2022, pp. 1–6, doi: 10.23919/SpliTech55088.2022.9854235.
2. M. M. Ahmadpanah, D. Hedin, M. Balliu, L. E. Olsson, and A. Sabelfeld, "SandTrap: Securing JavaScript-driven trigger-action platforms," in *Proc. 30th USENIX Security Symp.*, 2021, pp. 2899–2916.
3. K. R. Popper, *The Logic of Scientific Discovery*. London, U.K.: Hutchinson, 1959.
4. Y. Jia and M. Harman, "An analysis and survey of the development of mutation testing," *IEEE Trans. Softw. Eng.*, vol. 37, no. 5, pp. 649–678, Sep. 2011, doi: 10.1109/TSE.2010.62.
5. *Risk Management — Guidelines*, ISO 31000:2018, International Organization for Standardization, Geneva, Switzerland, 2018.
6. T. R. Thingnes and P. H. Meland, "Security challenges for users of extensible smart home hubs: A systematic literature review," *Future Internet*, vol. 17, no. 6, Art. no. 238, 2025, doi: 10.3390/fi17060238.

## Action Plan for the Next Reporting Period

**Priority tasks**

1. Prepare the interim report on its template by 6 November, from the current report.
2. Write the AI Use Disclosure appendix and the AI-use log for the final report.
3. Final build: complete the front matter, run F18 if a spare card is available, and give the supervisor the final draft to review.
4. Prepare for the defence: build a tool-calling agent that questions me on the report the way the AI jury member would. It will be grounded in the report and the result files, and I will test it on a set of known weak points.

**Expected outputs / evidence**

1. The interim report as a PDF.
2. The disclosure appendix and the log, with every accepted and rejected AI output traced to the repository.
3. The final report as a PDF, signed by the supervisor.
4. The agent's code, its evaluation set and the scored results.

**Risks / support needed**

- A spare memory card for F18.
- The declaration wording from the programme handbook.
- Confirmation from the supervisor or coordinator of the AI juror's format, and whether a clearly labelled answering agent may take part in the defence.

## AI Evidence Box – Diary 2

**AI tool / agent used.** Claude Code (Anthropic, Claude Opus model), in a terminal with access to the
repository and, over SSH, to the Pi. It is configured with persistent instruction files and a writing skill
for academic style.

**Task assigned to the AI.** Fixing defects found while writing and running the final rerun on the Pi
(build); checking numbers and screening the literature search (validation); drafting and typesetting the
report (communication).

**Representative prompts / instructions / configuration.** "Predictions are fine, go ahead" (after I read
the committed predictions); "Section 9 is fine. Make the fixes." Standing instructions: third person, academic
style, commit only named files, no credentials in the chat. I set the decision gates, e.g. no fix to F57 before my
review of the architecture.

**Relevant AI output.** Fixes with prediction notes (F54, F57–F61), the final rerun's results
(`experiments/verify/results/final_20261016/`), section drafts, the screening table and the read-through notes.

**Human verification performed.** I approved each section before the next, read the predictions before the
rerun, and reviewed every paper classed as adjacent plus 20 random exclusions (all agreed). Numbers were checked against the final results, references
against Crossref, and one disputed count was re-measured on the Pi.

**What was accepted, modified, or rejected.** Errors found in the AI's output, all corrected:

- "38 integrations declare permissions" counted manifest files; the true figure is 0 of 75.
- Stale counts in drafted text (findings to F56; 40 defects, not 53).
- The AI-written fault scripts missed the approval step (F61).
- Of five papers the AI classed as adjacent, I kept one.
- I rolled back wording narrowed on an abstract alone.

I chose which trims to apply. The design decisions were mine (fixing F54, approval for every manifest, one
final rerun).

**Ethical / confidentiality / reliability considerations.** Credentials stay on the Pi and are scanned for
before every push. With an AI-assisted build there was no independent adversary, so the security results are
stated as resting on the project's own attacks. AI use will be declared in the final report, and I am following
a curriculum so that I can explain the code myself.

---

## Notes for Younes (not part of the diary)

- **Check every claim about your own actions.** I wrote "I reviewed every screening decision" and "I read the predictions" from the project record. Change anything that isn't accurate.
- **P3CRID** was the one adjacent paper the search kept. The search summary says it supports §7's gap sentence, but the submission doesn't cite it. Should it be added to §7 and to these references?
- **The S4 ethics material** (credentials, the independent adversary, attribution) is used here in short form, and the AI-skills plan builds it out.
