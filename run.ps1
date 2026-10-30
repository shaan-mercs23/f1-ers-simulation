# PowerShell Launcher for F1 ERS Simulation Suite
param(
    [string]$Command = "",
    [string]$Drivers = "ver,ham,alo,nor",
    [string]$Track = "monza",
    [string]$HtmlReport = "f1_comparison_report.html",
    [switch]$Web,
    [switch]$Test
)

$pyPaths = @(
    "C:\Users\shaan\AppData\Local\Programs\KiCad\10.0\bin\python.exe",
    (Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source),
    (Get-Command py -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
)

$py = $null
foreach ($p in $pyPaths) {
    if ($p -and (Test-Path $p)) {
        $py = $p
        break
    }
}

if (-not $py) {
    Write-Error "Python executable not found. Please install Python 3.9+."
    exit 1
}

if ($Test) {
    & $py -m unittest discover tests
} elseif ($Web) {
    & $py app.py 8050
} elseif ($Command -ne "") {
    & $py cli.py $args
} else {
    & $py cli.py compare --drivers $Drivers --track $Track --html-report $HtmlReport
}
