## Appendix J — AI Use Disclosure

### J.1 Tool and model

All AI assistance in this project came from one tool: Claude Code, Anthropic's command-line agent, running models of the Claude Opus family (Anthropic, 2026). I used it from the start of the rebuild on 21 August 2026 to the submission of this report. No other AI tool produced any part of the code, the measurements or the text.

Claude Code worked inside the project's repository on the development laptop and, over SSH, on the Raspberry Pi 5 used as the reference device. It could read and write files, run commands and commit to the local repository. Its work reached GitHub only when I approved a push, and before every push an exact-value scan checked that none of my credentials appeared in any commit.

### J.2 How the tool was instructed

The tool was instructed in two ways. The first was conversation: each working session began with my request and continued with my answers to its questions and my decisions on its proposals. The second was a set of persistent instruction files that carried my standing rules from one session to the next. These files recorded, among other things, that the report is written in the third person except for its AI-use material and its learning strategies, that it uses APA 7, that the integrations it studies are called "community integrations", that a file is never deleted through a wildcard, that only named files are committed, and that every correction to the AI's output is added to the AI-use log. A hand-over file recorded where the work stood and which decisions were still open.

### J.3 Representative instructions

The project ran over many sessions, so this appendix gives a representative sample of my instructions rather than every prompt. Each instruction in Table J.1 is quoted from the project's records, with its date and what it produced.

**Table J.1**
*A representative sample of my instructions and what each produced*

| Date | My instruction | What it produced |
|---|---|---|
| 2026-10-10 | "section 9 is fine. make the fixes" | Approval of the architecture chapter, then fixes for two defects (F57, F58), each with a prediction and a test that failed first |
| 2026-10-14 | "keep it planned" | The documented literature search was committed as a protocol but not yet run |
| 2026-10-16 | "predictions are fine go ahead" | The first full rerun of every experiment, under predictions committed beforehand |
| 2026-10-25 | "the list is fine. Just be careful about what is passed and potential injection" | The commands a household may send to a confined device were limited to named fields of a fixed type; anything else is refused and logged without its content |
| 2026-10-25 | "go ahead with the fix" | The fix for F65, a defect that stopped every sandbox's web component from starting |
| 2026-10-26 | "we fix it" | A fix for F68 rather than a recorded limit, with its prediction and failing test committed first |
| 2026-10-31 | State the lock code format "as a limit" | The final report states this limit rather than adding code to work around it |
| 2026-11-01 | Freeze the code | Only defects found while writing may be fixed; no new features or experiments |
| 2026-11-04 | "the new work done for extending device types won't be included in the interim report. They will be included in the final report." | The interim report kept its 27 October figures; the bridge extension is reported here |

My instructions also included questions, and one of them changed how the project was tested. I asked whether the test suites did more than confirm what the code already did, and the answer was a campaign of deliberate defects planted in the code to check that the suites catch them (Section 13.2).

### J.4 How the output was used and modified

The output of the tool was never used without a human check, and the check depended on the kind of output.

For **code**, I approved each design before it was written, usually by choosing among options the tool laid out with its recommendation. A prediction note was then committed, a test was shown to fail, and only then was the change made. The change was accepted only when the test passed and every other suite still passed, and the experiments were then rerun against the real platform. When the tool's recommendation was wrong for the project, I decided otherwise, as when I chose to fix F68 rather than record it.

For **measurements**, the pass criteria were committed before each run, and each figure in this report was checked against its raw result file. The tool's reading of a result was not accepted on its own: two complete reruns of every experiment, on 16 October and 1 November 2026, recomputed the reported figures from the raw data.

For the **literature search**, the tool screened the records, and I reviewed every record it classed as relevant or adjacent and a seeded random sample of 20 exclusions (Section 13.3).

For **text**, the tool drafted each section of this report from the project's records. I reviewed each section and either approved it, rewrote parts of it myself or sent it back with changes, and no section was started until the one before it was approved. Some of my changes were edits of my own, such as the sentence I cut from Section 11, the subsections I dropped from Sections 10 and 14, and my trim of the acknowledgements. Others were rejections, such as the closing paragraph I dropped from Section 7 and the removal of sentences I judged unnecessary. Every case in which the tool's text was wrong, overstated or rejected is recorded in the AI-use log (Appendix K).

### J.5 Confidentiality and responsibility

The tool worked with the project's code, the public source code of the integrations studied, and my own test accounts with online services. No personal data from anyone else was given to it. The credentials for my test accounts stayed on the reference device, and the scan before each push confirmed that none reached the repository.

I remain responsible for every part of this report and the work it describes. Where the tool's output is in the final version, I have checked it against the project's records and understood it well enough to defend it.
