# setup.ps1 — Install all dependencies needed to run hw2 (Docker Compose + Kubernetes/Kind)
# Run from the project root: .\scripts\setup.ps1

$ErrorActionPreference = "Stop"

function Test-Command($cmd) {
    return [bool](Get-Command $cmd -ErrorAction SilentlyContinue)
}

function Write-OK($msg)   { Write-Host "  [OK]  $msg" -ForegroundColor Green }
function Write-Skip($msg) { Write-Host "  [--]  $msg" -ForegroundColor Yellow }
function Write-Installing($msg) { Write-Host "  [>>]  $msg" -ForegroundColor Cyan }

Write-Host "`nhw2 dependency setup`n" -ForegroundColor White

# ── Docker ────────────────────────────────────────────────────────────────────
if (Test-Command "docker") {
    Write-OK "Docker $(docker --version)"
} else {
    Write-Host "  [!!]  Docker not found." -ForegroundColor Red
    Write-Host "        Install Docker Desktop from https://www.docker.com/products/docker-desktop/" -ForegroundColor Red
    exit 1
}

# Confirm Docker daemon is running
try {
    docker info | Out-Null
    Write-OK "Docker daemon is running"
} catch {
    Write-Host "  [!!]  Docker is installed but not running. Start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# ── kubectl ───────────────────────────────────────────────────────────────────
if (Test-Command "kubectl") {
    Write-OK "kubectl $(kubectl version --client --short 2>$null)"
} else {
    Write-Installing "Installing kubectl via winget..."
    winget install --id Kubernetes.kubectl --silent --accept-source-agreements --accept-package-agreements
    Write-OK "kubectl installed"
}

# ── kind ──────────────────────────────────────────────────────────────────────
if (Test-Command "kind") {
    Write-OK "kind $(kind version)"
} else {
    Write-Installing "Installing kind via winget..."
    winget install --id Kubernetes.kind --silent --accept-source-agreements --accept-package-agreements
    # Refresh PATH so kind is available immediately
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("PATH", "User")
    if (Test-Command "kind") {
        Write-OK "kind installed"
    } else {
        # Fallback: download binary directly
        Write-Installing "winget install failed, downloading kind binary directly..."
        $kindUrl = "https://kind.sigs.k8s.io/dl/v0.23.0/kind-windows-amd64"
        $kindDest = "$env:USERPROFILE\.local\bin\kind.exe"
        New-Item -ItemType Directory -Force "$env:USERPROFILE\.local\bin" | Out-Null
        Invoke-WebRequest -Uri $kindUrl -OutFile $kindDest
        $env:PATH += ";$env:USERPROFILE\.local\bin"
        [System.Environment]::SetEnvironmentVariable(
            "PATH",
            [System.Environment]::GetEnvironmentVariable("PATH","User") + ";$env:USERPROFILE\.local\bin",
            "User"
        )
        Write-OK "kind installed to $kindDest (added to PATH)"
    }
}

# ── Summary ───────────────────────────────────────────────────────────────────
Write-Host "`nAll dependencies satisfied. You can now run:`n" -ForegroundColor Green
Write-Host "  Docker Compose:   docker compose up -d --build"
Write-Host "  Kubernetes:       kind create cluster --name hw2 --config k8s/kind-config.yaml`n"
