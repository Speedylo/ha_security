# 13. AI Use, Evaluation and Evidence

## 13.1 AI tool and purpose

I used one AI tool throughout the project: Claude Code, Anthropic's command-line agent, running models of the Claude Opus family (Anthropic, 2026). It is an agent rather than a chat interface. It reads and writes files in the project's repository and runs commands on the development laptop and, over SSH, on the Raspberry Pi 5 that serves as the reference device. Persistent instruction files configured its behaviour across sessions, recording the project's working rules and my standing decisions.

I chose an agent because most of the work is code, measurements on a remote device and long technical prose. An agent that acts on the repository and the device directly suits those tasks better than a chat tool, whose output has to be copied across by hand. That ability is also the main risk. An agent that can run a measurement can also misread one and report the misreading, and an agent that can write files can overwrite them. The rest of this section describes how I controlled that risk and what the evidence shows about how well the controls worked.

## 13.2 AI-assisted activities and human verification

AI assistance covered four kinds of activity, and each one was paired with its own human check (Table 13.1).

**Table 13.1**
*AI-assisted activities and the human verification applied to each*

| Activity | What the AI did | Human verification |
|---|---|---|
| Implementation | Wrote and modified the confinement framework, the experiment scripts and the fixes for defects found during evaluation | Each design decision was approved before any code was written; each fix was preceded by a committed prediction and by a test shown to fail without the fix |
| Measurement | Ran the experiments on the reference device and wrote the results to committed files | Predictions and pass criteria were committed before each run; every reported figure was checked against the raw result files |
| Literature search | Ran the documented database search and screened records on titles and abstracts | I reviewed every record classed as relevant or adjacent and a random sample of 20 exclusions |
| Writing | Drafted report sections, diaries and figures from the project's records | I reviewed and approved each section before the next was started |

The extension of the bridge after the interim report shows how these checks worked on new code. The bridge lets a confined integration provide devices to the household's installation, and at the interim it covered 11 kinds of device. Extending it to 29 kinds took five batches, and every batch followed the same order: a prediction note was committed, a test was shown to fail, the change was made, and the integrations were then run again against a real installation. Claude proposed the design of each batch, and I decided it. For cameras, for example, I chose still snapshots over live video, with a 512 KiB cap on each picture, and accepted that three integrations would lose live video as a stated limit. For locks, I decided that an integration-supplied code format would be stated as a limit rather than engineered around.

The decisions that shaped the project as a whole were also mine. They include requiring the owner's approval before any sandbox starts, fixing a defect found late in evaluation rather than recording it, freezing the code on 1 November 2026 so that only defects found while writing could be fixed, and deciding to rerun every experiment a second time, at the frozen code, before the results were written. My instructions also steered the work rather than only approving it. When I approved the list of commands a household may send to a confined device, I added "be careful about what is passed and potential injection", and each command now accepts only named fields of a fixed type. When every test suite passed, I asked whether the suites did more than confirm what the code already did. The answer was to plant deliberate defects in the code and check that the suites caught them, a practice known as mutation testing, and it found gaps the suites had missed.

Across these activities, the AI produced most of the volume of the work, while the decisions and the checks on its output stayed with me. Whether those checks were effective is a question of evidence, which the next subsection addresses.

## 13.3 Evaluation of AI output

I evaluated the AI's output in three ways: through checks built into the research method, through structured human review, and through a log of every error found.

The first check is part of the method itself. Every experiment's predictions and pass criteria were committed to the repository before it ran, and a script confirms that each prediction note predates the results it covers. An AI therefore cannot quietly adjust a criterion to fit a result. The test suites were tested in turn. At the final rerun, 92 deliberate defects were planted in the code one at a time. The suites caught 90 of them. Each of the other two changed nothing the code does, so no test could have caught it.

The second check is human review, and the literature search shows how it was structured. Claude screened 642 distinct records, excluded 590 on their titles and, of the 52 screened on their abstracts, classed five as adjacent to the project's research gap. I reviewed all five and kept one, which shows that the AI's relevance judgements were too generous. I checked the exclusions the other way, through a random sample of 20 drawn with a fixed seed, and agreed with all 20. The sample does not prove that no relevant paper was missed, but it limits the risk. I adopted the same approach, full review of positive judgements and a seeded sample of negative ones, for any later bulk judgement made by the AI.

The third check is a log of every correction made to AI output, kept since 23 October 2026, with six earlier entries reconstructed from the project's records. It holds 40 entries (Table 13.2). One records a risk rather than an error: the 590 title exclusions were the AI's alone, apart from the sample.

**Table 13.2**
*The 40 entries of the AI-use log, by kind*

| Kind | Entries | Example |
|---|---|---|
| Errors of fact, count or code | 13 | A count of 38 integrations "declaring permissions" had counted configuration files; re-measured on the device, the true figure was 0 of 75 |
| Test assumptions that were wrong while the code was right | 5 | A check expected a new device to show no state, which holds only on a freshly installed platform |
| Errors of judgement, planning or method | 10 | The project's claims were narrowed to fit a paper of which only the abstract had been read; the change was rolled back |
| Overclaims about my role, a source or a result | 11 | "I reviewed every screening decision", when I had reviewed the adjacent records and a sample, not all 590 title exclusions |
| A risk, not an error | 1 | The title screen, above |

The errors were caught by the method's own checks, by my review, or by Claude's checks against the project's records before a draft was shown. None was accepted because the tool seemed reliable. Taken together, the three checks show that AI output in this project was wrong often enough that none of it could be accepted unverified, and that the process caught those errors.

## 13.4 Critical reflection and limitations

The evidence supports some conclusions about the AI's reliability and leaves others open. Its recurring weakness was overstatement. Counts were stale or computed over the wrong set, a source was summarised more strongly than it reads, a result was stated for more integrations than it covered, and my own part was described as larger than it was. I caught each instance by reading the text against what had actually been done, which is a check no automated test performs.

The bridge extension added two patterns that the interim report could not show. Five times, a test or prediction the AI wrote was wrong while the code was right, and three of these tests assumed a platform holding little or no state, so they passed on a fresh installation and failed on a used one. Counts were also carried forward from earlier work without being recounted, such as a coverage figure that treated one integration as fully supported after an earlier batch had recorded the gap. A further entry concerns an action rather than text. The agent ran a script with a help option the script did not have, and the script regenerated fourteen committed records. Version control restored them, but the episode shows that an agent's mistakes can change the record as well as misdescribe it.

A second risk is automation bias, the tendency to scrutinise an automated system's output less as it proves reliable (Parasuraman & Manzey, 2010). This risk grows as the AI's output exceeds what one person can read line by line. The project answered it with checks that do not depend on the reviewer's attention: predictions committed before results, recomputation of every reported figure from the raw data, mutation testing and sampled review. These checks have limits of their own, and the 590 title exclusions remain the clearest example.

The most important limitation concerns independence. The same AI-assisted process that built the confinement framework also wrote the attacks used to evaluate it, and a planned evaluation by an independent adversary was dropped from the project's scope. The security results therefore rest on the project's own attacks, not on independent testing, and they are stated that way wherever they are reported. These limits do not overturn the results, but they set how far the results can be trusted.

## 13.5 Supporting AI evidence

The evidence behind this section is open to inspection in the project's repository (Appendix A). The AI Use Disclosure (Appendix [AI-D]) names the tool and models, gives a representative sample of my instructions with what each produced, and describes how the output was used and changed. The full AI-use log, with the date, deliverable, output, error, how it was caught and the correction for each entry, is reproduced in Appendix [AI-LOG]. The repository also holds the literature search's screening table with my review sheet and the committed prediction notes and result files of every experiment, including both final reruns. The AI Evidence Boxes for Diaries 1 and 2 were submitted with those diaries.

This report was prepared the same way as the work it describes. Claude Code drafted each section from the project's records, and I reviewed, corrected and approved each one, with every correction added to the log. The project's contribution here is a working example of AI-assisted engineering in which every AI output was treated as a claim to be checked, together with the record of what those checks found.
