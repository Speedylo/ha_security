# The final report

The final report in the programme's template, one Markdown file per section, `00_front_matter.md` to
`22_appendix_h_ai_use_log.md`; the references are in APA 7 (`17_references.md`), Appendices A–D are in
`18_appendices.md`, and Appendices E–H have a file each. The appendices in full, before they were cut
for length, are in `../notes/appendices_full_20261110/`.

- `build_final.py` fills the programme's report template (the interim report's format) with the
  sections and writes `final_report.docx`; it reuses `../interim/build_interim.py`'s template handling.
- `../interim/render_word.ps1` opens that file in Microsoft Word, fills the contents and the lists of
  figures and tables, and exports `final_report.pdf` (and Word's filled copy with `-OutDocx`).
- `build_docx.py` is the October build, without the template; superseded.

The report was condensed from the working report in `../report/`, against which every claim was
registered and checked (`../verify/`).
