param(
    [string]$Port = "8000",
    [string]$EnvFile = ".env"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendPath = Join-Path $ProjectRoot "backend"

# Copy .env if not present
$EnvPath = Join-Path $BackendPath ".env"
if (-not (Test-Path $EnvPath)) {
    $ExamplePath = Join-Path $ProjectRoot $EnvFile
    if (Test-Path $ExamplePath) {
        Copy-Item $ExamplePath $EnvPath
        Write-Host "Created .env from $EnvFile"
    }
}

& "pip" install -r (Join-Path $BackendPath "requirements.txt") --quiet

Set-Location $BackendPath
& "python" -m uvicorn app.main:app --host 0.0.0.0 --port $Port
