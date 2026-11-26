param(
    [string]$DocxPath = "output/report/sdn-track-1-report.docx",
    [string]$PdfPath = "output/report/sdn-track-1-report.pdf",
    [switch]$Validate,
    [switch]$UseWordPdf
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
function Resolve-ProjectPath([string]$p) {
    if ([IO.Path]::IsPathRooted($p)) { return [IO.Path]::GetFullPath($p) }
    return [IO.Path]::GetFullPath((Join-Path $ProjectRoot $p))
}

$docxAbs = Resolve-ProjectPath $DocxPath
$pdfAbs  = Resolve-ProjectPath $PdfPath

if (-not (Test-Path -LiteralPath $docxAbs)) {
    throw "DOCX file not found: $docxAbs"
}

$pdfDir = Split-Path -Parent $pdfAbs
if ($pdfDir -and -not (Test-Path -LiteralPath $pdfDir)) {
    New-Item -ItemType Directory -Path $pdfDir -Force | Out-Null
}

if ($Validate) {
    $validator = "C:\Users\Fouad\.gemini\config\skills\docx\scripts\office\validate.py"
    if (Test-Path -LiteralPath $validator) {
        Write-Host "Running OOXML XSD validation..."
        & py -3.14 $validator $docxAbs
        if ($LASTEXITCODE -ne 0) {
            throw "OOXML validation failed with exit code $LASTEXITCODE"
        }
    }
}

# Step 1: Refresh all live Word fields (TOC, PAGE, NUMPAGES) via Word 16.0 COM and save DOCX
$word = $null
$doc  = $null
$wordPages = $null

try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0          # wdAlertsNone
    $word.ScreenUpdating = $false
    try { $word.Options.UpdateFieldsAtPrint = $true } catch {}

    $doc = $word.Documents.Open($docxAbs, $false, $false)

    # Enforce compact 1-page TOC styling so Word TOC never spills onto page 4
    try {
        $st1 = $doc.Styles.Item("TOC 1")
        $st1.Font.Name = "Segoe UI"; $st1.Font.Size = 8.5; $st1.Font.Bold = 1
        $st1.ParagraphFormat.SpaceBefore = 2.0; $st1.ParagraphFormat.SpaceAfter = 0.5
        $st1.ParagraphFormat.LineSpacingRule = 4; $st1.ParagraphFormat.LineSpacing = 10.5
        $st2 = $doc.Styles.Item("TOC 2")
        $st2.Font.Name = "Segoe UI"; $st2.Font.Size = 7.8; $st2.Font.Bold = 0
        $st2.ParagraphFormat.SpaceBefore = 0.0; $st2.ParagraphFormat.SpaceAfter = 0.0
        $st2.ParagraphFormat.LineSpacingRule = 4; $st2.ParagraphFormat.LineSpacing = 9.4
    } catch {}

    $doc.Repaginate()
    foreach ($toc in $doc.TablesOfContents) {
        $toc.Update()
    }
    $doc.Fields.Update() | Out-Null

    foreach ($story in $doc.StoryRanges) {
        $range = $story
        while ($null -ne $range) {
            try { $range.Fields.Update() | Out-Null } catch {}
            $range = $range.NextStoryRange
        }
    }

    $doc.Repaginate()
    foreach ($toc in $doc.TablesOfContents) {
        $toc.UpdatePageNumbers()
    }
    foreach ($story in $doc.StoryRanges) {
        $range = $story
        while ($null -ne $range) {
            try { $range.Fields.Update() | Out-Null } catch {}
            $range = $range.NextStoryRange
        }
    }

    $doc.Repaginate()
    $wordPages = $doc.Range($doc.Content.End - 1, $doc.Content.End - 1).Information(4)  # wdNumberOfPagesInDocument
    if (-not $wordPages -or $wordPages -le 1) {
        $wordPages = $doc.ComputeStatistics(2)
    }
    Write-Host "--- WORD HEADING PAGES ---"
    foreach ($p in $doc.Paragraphs) {
        $s = $p.Style.NameLocal
        if ($s -eq "Heading 1" -or $s -eq "Front Heading") {
            $pg = $p.Range.Information(3)
            $txt = ($p.Range.Text -replace "[\r\n]","").Trim()
            Write-Host ("  WORD p.{0:D2} | {1}" -f $pg, $txt)
        }
    }
    $doc.Save()

    if ($UseWordPdf) {
        $doc.ExportAsFixedFormat(
            $pdfAbs, 17, $false, 0, 0, 1, 1, 0, $true, $true, 1
        )
    }
}
finally {
    if ($null -ne $doc) {
        try { $doc.Close([ref]0) } catch {}
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($doc)
    }
    if ($null -ne $word) {
        try { $word.Quit([ref]0) } catch { try { $word.Quit() } catch {} }
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}

Write-Host ("Updated DOCX TOC & fields via Word 16.0 COM: {0} | Word Pages: {1}" -f $docxAbs, $wordPages)

# Step 2: Export matching publication PDF via Chrome headless (2-pass TOC sync + pypdf heading bookmarks)
if (-not $UseWordPdf) {
    $builder = Join-Path $PSScriptRoot "build_report.py"
    & py -3.14 $builder --pdf-only --pdf $pdfAbs
    if ($LASTEXITCODE -ne 0) {
        throw "Print-PDF export failed with exit code $LASTEXITCODE"
    }
}

if (-not (Test-Path -LiteralPath $pdfAbs)) {
    throw "PDF export failed; output file not created: $pdfAbs"
}

$docxBytes = (Get-Item -LiteralPath $docxAbs).Length
$pdfBytes  = (Get-Item -LiteralPath $pdfAbs).Length
$pyPages   = (& py -3.14 -c "import pypdf, sys; print(len(pypdf.PdfReader(sys.argv[1]).pages))" $pdfAbs).Trim()
Write-Host ("DONE | DOCX: {0:N0} KB ({1} Word pages) | PDF: {2:N0} KB ({3} PDF pages)" -f ($docxBytes / 1KB), $wordPages, ($pdfBytes / 1KB), $pyPages)
