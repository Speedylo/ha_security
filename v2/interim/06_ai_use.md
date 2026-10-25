# 6 AI Use, Evaluation and Evidence

## 6.1 AI tools and purpose

A single AI tool was used throughout the project: Claude Code, Anthropic's command-line agent, running models of the Claude Opus family (Anthropic, 2026). It is an agent rather than a chat interface. It reads and writes files in the project's repository, runs commands on the development laptop and, over SSH, on the Raspberry Pi 5 that serves as the reference device. Its behaviour was configured by persistent instruction files. These carry the project's working rules: write in the third person, commit only the files named, never place a credential in the conversation, and load a writing skill for academic style before drafting report text.

The tool was chosen for one reason. The work consists mostly of code, measurements on a remote device and long technical prose, and an agent that can act on the repository and the device directly suits those tasks better than a chat tool, whose output must be copied by hand. That same capacity is also the main risk: an agent that can run a measurement can also report one that it misread. The rest of this section describes how that risk was controlled.

## 6.2 AI-assisted research activities

AI assistance covered four kinds of research activity, and each one was paired with its own human check (Table 6.1).

**Table 6.1**
*AI-assisted activities and the human verification applied to each*

| Activity | What the AI did | Human verification |
|---|---|---|
| Implementation | Wrote and modified the confinement framework, experiment scripts and fixes for defects found during evaluation | Each fix was preceded by a committed prediction and a test shown to fail without the fix; the author approved every design decision before any code was written |
| Measurement | Ran the experiments on the reference device and wrote the results to committed files | Predictions and pass criteria were committed before each run; every reported figure was checked against the raw result files |
| Literature search | Ran the documented database search and screened records on titles and abstracts | The author reviewed every record classed as relevant or adjacent and a random sample of 20 exclusions |
| Writing | Drafted report sections, diaries and figures from the project's records | The author reviewed and approved each section before the next was started |

The author retained responsibility for every decision that shaped the project. Examples are the choice to require an owner's approval before any sandbox starts, the decision to fix a defect found late in evaluation rather than record it, and the decision to run one final full rerun before writing up. Representative instructions show this division of labour. After reading the committed predictions, the author's instruction "Predictions are fine, go ahead" started the final rerun, and "Section 9 is fine. Make the fixes" released a set of corrections only after the author had reviewed the whole section. Some work was deliberately held back: no fix to the approval defect was started until the author had read the system-architecture chapter and given all feedback on it.

The pattern across these activities is that the AI produced the volume of the work while the decisions, and the checks on it, stayed with the author. Whether those checks worked is a question of evidence, which the next subsection addresses.

## 6.3 AI output evaluation

The AI's output was evaluated in three ways: by checks built into the research method, by structured human review, and by a log of every error found.

The first check is methodological. Every experiment's predictions and pass criteria were committed to the repository before it ran, and a script checks that each prediction note was committed before the results it covers. An AI cannot then quietly adjust a criterion to fit a result. The test suites were themselves tested by mutation: 53 deliberate defects were introduced into the code, and the suites detected 52 of them, the remaining one being equivalent to the original code. The method also caught an AI error that review had missed. The final full rerun showed that AI-written fault-injection scripts had never been updated when the owner's approval step became mandatory, so every fault case stopped at its first start. The fault results then on record had come from scripts that predated the approval step. The defect was recorded, fixed under its own tag and rerun.

The second check is human review, and the literature search shows how it was structured. Claude screened 642 distinct records: 590 were excluded on their titles, and of the 52 screened on their abstracts, five were classed as adjacent to the project's gap. The author then reviewed all five and kept only one, which shows that the AI's relevance judgements were too generous. The exclusions were checked the other way. A random sample of 20 excluded records, drawn with a fixed seed, was reviewed by the author, who agreed with all 20. The sample does not prove that no relevant paper was missed, but it bounds the risk, and the method is stated in the search protocol. The same approach of full review of positive judgements and a seeded sample of negative ones was adopted for any later bulk judgement made by AI.

The third check is a log of every correction made to AI output, kept since 23 October 2026, with earlier entries reconstructed from the project's records. Of its 14 entries, one records a risk rather than an error, and the other 13 fall into three groups. Four are errors of fact, count or code, such as a count of 38 integrations "declaring permissions" that had in fact counted configuration files; the true figure, re-measured on the device, was 0 of 75. Five are errors of judgement or planning, such as treating the syllabus's dates as authoritative. The remaining four are overclaims, and three of those overstate the author's own role or verification, for example "I reviewed every screening decision" when the author had reviewed the adjacent records and a sample, not all 590 title exclusions. The fourth overstated a source: a 2026 threat-modelling paper was summarised as naming Home Assistant integrations as an attack vector, when a rereading of its full text showed that it names integrations in general.

Taken together, the three checks show that AI output in this project was wrong often enough that none of it could be accepted unverified, and that the errors were caught by the method and by review rather than by trust in the tool.

## 6.4 Critical reflection and limitations

The evidence above supports some conclusions about the AI's reliability and leaves others open. Its recurring weakness was not invention but overstatement. Counts were stale or computed over the wrong set, a source was summarised more strongly than it reads, and the human's own part was described as larger than it was. This last pattern matters because overclaiming in a disclosure is the error that a disclosure is meant to prevent. The author caught each instance by reading the text against what had actually been done, which is a check no automated test performs.

A second risk is automation bias, the tendency to accept an automated system's output with less scrutiny as it proves reliable (Parasuraman & Manzey, 2010). It grows as the volume of AI output exceeds what one person can examine line by line. The project answered it with structural checks that do not rely on the reviewer's attention: predictions committed before results, recomputation of every figure from raw data, mutation testing and sampled review. These checks have limits of their own. The 590 title exclusions were made by the AI alone apart from the 20 sampled, and once a credential scan was run in its weaker, pattern-only form because the reference device was switched off. That scan remains owed in its exact form.

The most important limitation concerns independence. The same AI-assisted process that built the confinement framework also wrote the attacks used to evaluate it, and a planned evaluation by an independent adversary was dropped from the project's scope. The security results are therefore stated as resting on the project's own attacks, not on independent testing. A related concern is ownership. Because much of the code was AI-assisted, the author is working through a curriculum on the underlying mechanisms, such as Linux namespaces, file-descriptor passing and the platform's internals, so that every part of the code can be explained and defended without the tool.

These limits do not undo the results, but they define how far the results can be trusted, and they are stated wherever the results are reported.

## 6.5 Supporting AI evidence

The evidence behind this section is kept in the project's repository and is open to inspection (Appendix A). It has four parts:

- The AI-use log of corrections, with the date, deliverable, output, error, how it was caught and the correction made (Appendix C).
- The literature search's screening table and the author's review sheet, which record both the AI's and the author's decision on every reviewed record.
- The committed prediction notes and the result files of every experiment, including the final rerun.
- The AI Evidence Boxes submitted with Diaries 1 and 2.

Table 6.2 gives one representative entry from each group in the log.

**Table 6.2**
*Representative entries from the AI-use log*

| AI output | What was wrong | How it was caught | Correction |
|---|---|---|---|
| "38 integrations declare permissions" | Counted configuration files, not declarations | Number check before submission; re-measured on the device | 0 of 75; text corrected |
| Fault-injection scripts | Omitted the mandatory approval step | The final full rerun | Fixed and rerun under its own tag |
| Five literature records classed as adjacent | Four did not bear on the gap | The author's review of every adjacent record | One kept |
| "I reviewed every screening decision" | Overstated the author's verification | The author's question about the review's scope | Rewritten to the actual scope |

The interim report itself was prepared the same way: Claude Code drafted each section from the project's records, and the author reviewed, corrected and approved each one, with corrections added to the log. The French résumé was drafted by Claude and checked by the author.

## References (for this section; to merge into the report's list)

Anthropic. (2026). *Claude Code* [Computer software]. https://claude.com/claude-code

Parasuraman, R., & Manzey, D. H. (2010). Complacency and bias in human use of automation: An attentional integration. *Human Factors, 52*(3), 381–410. https://doi.org/10.1177/0018720810376055
