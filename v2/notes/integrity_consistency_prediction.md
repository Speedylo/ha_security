# Evidence integrity, document consistency, citations (verification 4.8–4.10): criteria, written before the checks

**2026-10-06.** Younes asked to skip 4.6 for now and do the rest. These three phases check the
record rather than the code, so each criterion below is about what git and the report contain. As
before, a criterion is judged as written, and anything that fails it is a finding (F36 onwards).

## 4.8 Evidence integrity

**Pre-registration.** There are 19 prediction notes (`notes/*_prediction.md`). For each, the commit
that first added it must be older than the first commit of any result file it predicts. The note
names its results by path, and those paths are what is checked. Then a stricter test: after the
first result was committed, the predictions themselves were never edited. Text can be *added* after
results (an "Outcomes" section, a dated correction); a prediction line that *changed or vanished*
fails. *Prediction:* every note passes the first test, since that has been the working rule
throughout. The second is less certain: notes written during August predate the convention of
appending outcomes, and some may have been edited in place. A note whose results are not
recognisable by path is reported as unchecked, not as passed.

**Secrets.** The whole history (`git log -p --all`) is searched for two things. The first is the
patterns of tokens and keys: JWTs, GitHub tokens, private-key blocks, and `password=` or
`token=` with a value. The second is the literal values of the credentials in
`~/.config/capstone/` on the Pi, which are read only by the scan and never printed. *Criterion:*
no match. *Prediction:* none; two pushes have already been scanned this way (F20 and today's).

**Results actually committed.** Every path a README in `experiments/` or a report chapter cites as
a result exists in git at `HEAD`. *Prediction:* a few misses, most likely `.log` files, because
`*.log` was ignored for a while before the rule was found.

## 4.9 Document consistency

1. `report/toc.py --check` passes. It already checks the contents page and the heading count.
2. Every `§` cross-reference in the report resolves to a heading that exists.
3. Every `[n]` citation is in the bibliography, and every bibliography entry is cited.
4. Every count the prose states matches the artefacts: 25 suites and the base self-test, 19 threats
   (15 demonstrated), 20 requirements, and the number of references.
5. The abstract, Chapter 7 and Chapter 8 state each shared figure identically. `recompute.py`
   already checks 39 headline claims across all their stated copies, 39/39. The submission draft in
   `v2/submission/` is stale by design (phase R rewrites it), so it is checked and reported but not
   corrected.

*Prediction:* (1) and (5) pass. (2) finds some stale references, since sections have been
renumbered and appended. (4) may find a count that was stale before F25's correction.

## 4.10 Citations

Each reference is checked against its source. The check covers the authors, title, venue or
publisher, year, and any identifier (DOI, ISBN, standard number and clause), and that the
sentence citing it says what the source says. Each is recorded as checked, with the date and what
was checked. The plan names known doubts: [18]'s venue, [25]'s clause numbers, [26]'s ISBN, and
the two standards awaiting verification in `rewrite_consolidation_backlog.md` §7.
