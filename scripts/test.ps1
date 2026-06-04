param(
    [string]$Path = "tests/",
    [string]$ExtraArgs = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendPath = Join-Path $ProjectRoot "backend"

Set-Location $BackendPath
Invoke-Expression "python -m pytest $Path -v --tb=short $ExtraArgs"
