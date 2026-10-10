param(
    [Parameter(Mandatory = $true)]
    [string]$Python
)

$ErrorActionPreference = 'Stop'
$interpreterPath = (Resolve-Path -LiteralPath $Python).Path
$repositoryRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$runRoot = Join-Path $repositoryRoot ('.windows-work/run-' + [guid]::NewGuid().ToString('N'))
$fixturePath = Join-Path $PSScriptRoot 'model.py'

foreach ($folderName in @('geometry-basic', ('Geometry test caf' + [char]0x00e9))) {
    $projectPath = Join-Path $runRoot $folderName
    New-Item -ItemType Directory -Path $projectPath -Force | Out-Null
    Copy-Item -LiteralPath $fixturePath -Destination (Join-Path $projectPath 'model.py')
    Push-Location -LiteralPath $projectPath
    try {
        & $interpreterPath model.py
        if ($LASTEXITCODE -ne 0) {
            throw "CAD verification failed in $projectPath (exit $LASTEXITCODE)"
        }
    }
    finally {
        Pop-Location
    }
}

Write-Host "Both CAD geometry checks passed. Results: $runRoot"
