# The final report

The final report in the programme's template, one Markdown file per section, `00_front_matter.md` to
`22_appendix_h_ai_use_log.md`; the references are in APA 7 (`17_references.md`), Appendices A–D are in
`18_appendices.md`, and Appendices E–H have a file each. The appendices in full, before they were cut
for length, are in `../notes/appendices_full_20261110/`, and earlier drafts of the sections are in
`../notes/report_drafts/`.

- `build_final.py` fills the programme's report template with the sections and writes
  `Younes_Rahati_Final_Report.docx`; it reuses `../interim/build_interim.py`'s template handling.
  The template itself (`Capstone_Interimreport_RESEARCH-1.docx`, expected in `v2/`) is the
  programme's and is not distributed here, so the build needs a copy of it.
- `render_word.ps1` opens that file in Microsoft Word, fills the contents and the lists of
  figures and tables, and exports `Younes_Rahati_Final_Report.pdf` (and Word's filled copy with `-OutDocx`).
- `build_docx.py` is the October build, without the template; superseded.
- `../verify/recompute_final.py` recomputes the report's figures from the raw results and checks the text.

The report was condensed from the project's working report, which is kept locally and not published,
and against which every claim was registered and checked (`../verify/`).
