# Open a .docx in Microsoft Word (via WSL: powershell.exe -File render_word.ps1 -In C:\...\in.docx -Pdf C:\...\out.pdf [-OutDocx C:\...\out.docx]),
# update the contents, list of figures and list of tables, export a PDF, and optionally save Word's copy
# with the fields filled. Paths must be Windows paths; the input is closed without saving, so only -OutDocx writes a .docx.
param([string]$In, [string]$Pdf, [string]$OutDocx = "")
$ErrorActionPreference = "Stop"
$w = New-Object -ComObject Word.Application
$w.Visible = $false
$w.DisplayAlerts = 0
try {
  $d = $w.Documents.Open($In, $false, $false, $false)
  foreach ($t in $d.TablesOfContents) { $t.Update() }
  $d.Fields.Update() | Out-Null
  foreach ($t in $d.TablesOfContents) { $t.Update() }
  $d.Repaginate()
  "pages: " + $d.ComputeStatistics(2)
  $d.ExportAsFixedFormat($Pdf, 17)
  if ($OutDocx -ne "") { $d.SaveAs2($OutDocx, 16) }
  $d.Close(0)
} finally { $w.Quit() }
