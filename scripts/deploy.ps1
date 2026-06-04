param(
    [string]$Action = "build",
    [Parameter(Position=0)]
    [string]$Tag = "mantle-vision:latest"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

switch ($Action) {
    "build" {
        docker build -t $Tag -f (Join-Path $ProjectRoot "backend" "Dockerfile") $ProjectRoot
        Write-Host "Built $Tag"
    }
    "run" {
        docker run -d --name mantle-vision `
            -p 8000:8000 `
            --env-file (Join-Path $ProjectRoot ".env") `
            $Tag
        Write-Host "Container mantle-vision started on port 8000"
    }
    "stop" {
        docker stop mantle-vision 2>$null
        docker rm mantle-vision 2>$null
    }
    "push" {
        Write-Host "Push to registry. Tag: $Tag"
    }
    default {
        Write-Host "Usage: deploy.ps1 <build|run|stop|push> [tag]"
    }
}
