param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$ChromePath = "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    [switch]$KeepTemporary,
    [switch]$CombinedOnly
)

$ErrorActionPreference = 'Stop'
$scratch = Join-Path ([IO.Path]::GetTempPath()) ('sdn-report-export-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $scratch | Out-Null
$word = $null
$exports = @()
try {
    if (-not (Test-Path -LiteralPath $ChromePath)) { throw 'Chrome is required for local HTML/PDF rendering.' }
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $reportNames = @('chapter-3-system-design', 'chapter-4-implementation', 'chapter-5-experiments-and-results', 'chapter-6-conclusion', 'sdn-track-1-report')
    if ($CombinedOnly) { $reportNames = @('sdn-track-1-report') }
    foreach ($base in $reportNames) {
        $doc = $null
        $html = Join-Path $scratch ($base + '.html')
        try {
            $doc = $word.Documents.Open((Join-Path $ProjectRoot ('output\report\' + $base + '.docx')), $false, $true)
            $doc.WebOptions.Encoding = 65001
            $doc.SaveAs2($html, 10)
        } finally {
            if ($null -ne $doc) { $doc.Close(0); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($doc) }
        }
        $text = [IO.File]::ReadAllText($html, [Text.Encoding]::UTF8)
        # Word exports page breaks on inline BR elements; print CSS needs a block.
        $text = $text -replace '<br\b[^>]*page-break-before:always[^>]*>', '<div style="break-before:page;page-break-before:always"></div>'
        # Word can leak a table's white text colour into the following body span.
        # These reports print on white pages, so restore those spans to black.
        $text = $text -replace 'color:\s*(white|#FFFFFF)(?=[;''"\s>])', 'color:#000000'
        $text = $text.Replace('charset=windows-1252', 'charset=utf-8')
        [IO.File]::WriteAllText($html, $text, (New-Object Text.UTF8Encoding($false)))
        $exports += [pscustomobject]@{Html=$html; Pdf=(Join-Path $scratch ($base + '.pdf')); Target=(Join-Path $ProjectRoot ('output\report\' + $base + '.pdf'))}
    }
    $guide = Join-Path $ProjectRoot 'output\pdf\sdn-arabic-lab-guide.html'
    if (-not $CombinedOnly) {
        $exports += [pscustomobject]@{Html=$guide; Pdf=(Join-Path $scratch 'guide.pdf'); Target=(Join-Path $ProjectRoot 'output\pdf\sdn-arabic-lab-guide.pdf')}
    }
    foreach ($item in $exports) {
        $arguments = @('--headless', '--disable-gpu', '--disable-background-networking', '--disable-component-update', '--disable-extensions', '--disable-sync', '--no-first-run', '--no-default-browser-check', '--no-pdf-header-footer',
            ('--user-data-dir="' + (Join-Path $scratch 'chrome-profile') + '"'), ('--print-to-pdf="' + $item.Pdf + '"'), ([System.Uri]$item.Html).AbsoluteUri)
        $process = Start-Process -FilePath $ChromePath -ArgumentList $arguments -PassThru -WindowStyle Hidden -Wait
        if ($process.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $item.Pdf)) { throw ('PDF export failed: ' + $item.Target) }
    }
    foreach ($item in $exports) {
        Copy-Item -LiteralPath $item.Pdf -Destination $item.Target -Force
        Write-Output $item.Target
    }
} finally {
    if ($null -ne $word) { $word.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word) }
    if ($KeepTemporary) {
        Write-Output ('Temporary rendering files: ' + $scratch)
    } else {
        $resolved = [IO.Path]::GetFullPath($scratch)
        $tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
        $reparse = Get-ChildItem -LiteralPath $resolved -Recurse -Force -ErrorAction SilentlyContinue | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }
        if ($resolved.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase) -and (Split-Path -Leaf $resolved).StartsWith('sdn-report-export-') -and -not $reparse) {
            Remove-Item -LiteralPath $resolved -Recurse -Force
        }
    }
}
