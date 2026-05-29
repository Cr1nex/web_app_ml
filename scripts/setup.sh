#!/usr/bin/env bash
# setup.sh — Install all dependencies needed to run webml (Docker Compose + Kubernetes/Kind)
# Run from the project root: bash scripts/setup.sh

set -euo pipefail

ok()       { echo "  [OK]  $*"; }
skip()     { echo "  [--]  $*"; }
installing(){ echo "  [>>]  $*"; }
err()      { echo "  [!!]  $*" >&2; exit 1; }

echo ""
echo "webml dependency setup"
echo ""

# ── Docker ────────────────────────────────────────────────────────────────────
if command -v docker &>/dev/null; then
    ok "Docker $(docker --version)"
else
    err "Docker not found. Install Docker Desktop (Mac/Windows) or docker-ce (Linux)."
fi

if docker info &>/dev/null; then
    ok "Docker daemon is running"
else
    err "Docker is installed but not running. Start Docker Desktop first."
fi

# ── kubectl ───────────────────────────────────────────────────────────────────
if command -v kubectl &>/dev/null; then
    ok "kubectl $(kubectl version --client --short 2>/dev/null || kubectl version --client)"
else
    installing "Installing kubectl..."
    OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
    ARCH="$(uname -m)"
    [ "$ARCH" = "x86_64" ] && ARCH="amd64"
    [ "$ARCH" = "aarch64" ] && ARCH="arm64"

    KUBECTL_VERSION=$(curl -sL https://dl.k8s.io/release/stable.txt)
    curl -sLo /tmp/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/${OS}/${ARCH}/kubectl"
    chmod +x /tmp/kubectl
    sudo mv /tmp/kubectl /usr/local/bin/kubectl
    ok "kubectl installed"
fi

# ── kind ──────────────────────────────────────────────────────────────────────
if command -v kind &>/dev/null; then
    ok "kind $(kind version)"
else
    installing "Installing kind..."
    OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
    ARCH="$(uname -m)"
    [ "$ARCH" = "x86_64" ] && ARCH="amd64"
    [ "$ARCH" = "aarch64" ] && ARCH="arm64"

    curl -sLo /tmp/kind "https://kind.sigs.k8s.io/dl/v0.23.0/kind-${OS}-${ARCH}"
    chmod +x /tmp/kind
    sudo mv /tmp/kind /usr/local/bin/kind
    ok "kind installed"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "All dependencies satisfied. You can now run:"
echo ""
echo "  Docker Compose:   docker compose up -d --build"
echo "  Kubernetes:       kind create cluster --name webml --config k8s/kind-config.yaml"
echo ""
