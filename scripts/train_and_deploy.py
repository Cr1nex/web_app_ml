"""
Train a new model against the in-cluster MLflow, promote it to @champion,
and tell the running ml-service pods to hot-swap.

Cross-platform — pure Python, no shell-isms. Works the same on Linux,
macOS, and Windows (PowerShell or cmd) as long as `kubectl` and
`python` are on PATH.

Examples (from repo root):

    python scripts/train_and_deploy.py                # train + promote + hot-reload
    python scripts/train_and_deploy.py --skip-train   # promote latest + reload only
    python scripts/train_and_deploy.py --version 3    # promote a specific version
    python scripts/train_and_deploy.py --restart      # use rollout-restart, not /reload
    python scripts/train_and_deploy.py --namespace dev

Environment overrides:

    MLFLOW_LOCAL_PORT (default 5000)
    ML_SERVICE_PORT   (default 5002)
    MODEL_NAME        (default PropertyValuationModel)
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ML_DIR = PROJECT_ROOT / "ml_service"

CYAN = "\033[36m"
YEL  = "\033[33m"
RED  = "\033[31m"
END  = "\033[0m"
# Windows cmd doesn't render ANSI unless the terminal is set up for it;
# we strip when stdout isn't a tty to keep logs clean in CI / pipes.
USE_COLOR = sys.stdout.isatty() and os.name != "nt" or os.environ.get("ANSICON")


def step(msg: str) -> None:
    if USE_COLOR:
        print(f"{CYAN}==>{END} {msg}", flush=True)
    else:
        print(f"==> {msg}", flush=True)


def warn(msg: str) -> None:
    if USE_COLOR:
        print(f"{YEL}   {msg}{END}", flush=True)
    else:
        print(f"   {msg}", flush=True)


def fail(msg: str) -> "NoReturn":  # type: ignore[name-defined]
    prefix = f"{RED}!! " if USE_COLOR else "!! "
    suffix = END if USE_COLOR else ""
    print(f"{prefix}{msg}{suffix}", file=sys.stderr, flush=True)
    sys.exit(1)


def need(tool: str) -> str:
    path = shutil.which(tool)
    if path is None:
        fail(f"{tool!r} not found on PATH")
    return path


def run(cmd: list[str], *, check: bool = True, cwd: Path | None = None,
        capture: bool = False) -> subprocess.CompletedProcess[str]:
    """Run a subprocess, surface its output by default."""
    return subprocess.run(
        cmd,
        check=check,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def kubectl(namespace: str) -> list[str]:
    """Common kubectl invocation prefix."""
    return [need("kubectl"), "-n", namespace]


@contextmanager
def port_forward(namespace: str, service: str, local_port: int, remote_port: int):
    """
    Open `kubectl port-forward` in a child process and kill it on exit.

    Polls /health (or just the TCP socket) until the tunnel responds, so
    callers can use the URL immediately after entering the context.
    """
    cmd = [*kubectl(namespace), "port-forward",
           f"svc/{service}", f"{local_port}:{remote_port}"]
    # Discard the port-forward's chatty stdout so it doesn't interleave
    # with our own progress logs.
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        url = f"http://localhost:{local_port}/health"
        deadline = time.time() + 15.0
        while time.time() < deadline:
            if proc.poll() is not None:
                fail("kubectl port-forward exited unexpectedly")
            try:
                with urllib.request.urlopen(url, timeout=1.0) as r:
                    if r.status == 200:
                        break
            except (urllib.error.URLError, ConnectionError, socket.timeout):
                pass
            time.sleep(0.25)
        else:
            fail("port-forward never became healthy on /health")

        yield
    finally:
        # Be polite on POSIX, brutal on Windows where SIGTERM is finicky.
        try:
            if os.name == "nt":
                proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
            else:
                proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


def resolve_latest_version(tracking_uri: str, model_name: str) -> str:
    """Ask the MLflow registry for the highest-numbered version."""
    # Local import — only this branch needs mlflow installed.
    from mlflow import MlflowClient

    client = MlflowClient(tracking_uri)
    versions = client.search_model_versions(f"name='{model_name}'")
    if not versions:
        fail(f"no registered versions found for model '{model_name}'")
    return max(versions, key=lambda v: int(v.version)).version


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="train_and_deploy",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--skip-train", action="store_true",
                   help="Skip training, just promote latest + reload.")
    p.add_argument("--restart", action="store_true",
                   help="Use 'kubectl rollout restart' instead of per-pod /reload.")
    p.add_argument("--version", default=None,
                   help="Promote this specific version (default: latest in registry).")
    p.add_argument("--namespace", default=os.environ.get("NAMESPACE", "webml"),
                   help="Kubernetes namespace (default: webml).")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    namespace = args.namespace
    mlflow_port = int(os.environ.get("MLFLOW_LOCAL_PORT", "5000"))
    api_port    = int(os.environ.get("ML_SERVICE_PORT",   "5002"))
    model_name  = os.environ.get("MODEL_NAME", "PropertyValuationModel")

    # Pre-flight
    need("kubectl")
    need("python")

    try:
        run([*kubectl(namespace), "get", "namespace", namespace], capture=True)
    except subprocess.CalledProcessError:
        fail(f"namespace '{namespace}' not found — is the cluster up? try: make kind-up")

    try:
        run([*kubectl(namespace), "get", "deployment", "mlflow"], capture=True)
    except subprocess.CalledProcessError:
        fail(f"deployment/mlflow not found in '{namespace}'")

    step("waiting for mlflow to be Ready")
    run([*kubectl(namespace), "rollout", "status", "deployment/mlflow", "--timeout=60s"])

    step(f"opening port-forward svc/mlflow → localhost:{mlflow_port}")
    with port_forward(namespace, "mlflow", mlflow_port, 5000):
        tracking_uri = f"http://localhost:{mlflow_port}"
        os.environ["MLFLOW_TRACKING_URI"] = tracking_uri
        step(f"MLFLOW_TRACKING_URI={tracking_uri}")

        # ── Train ────────────────────────────────────────────────────────────
        if not args.skip_train:
            features_parquet = ML_DIR / "data" / "processed" / "features.parquet"
            if features_parquet.exists():
                warn(f"{features_parquet.relative_to(PROJECT_ROOT)} exists — reusing it")
            else:
                step("building feature parquet (one-time)")
                run([sys.executable, "-m", "src.data.transaction_features"], cwd=ML_DIR)

            step("training with --cv (this can take a few minutes)")
            run([sys.executable, "-m", "src.services.train", "--cv"], cwd=ML_DIR)
        else:
            warn("--skip-train set; not training")

        # ── Resolve + promote ────────────────────────────────────────────────
        version = args.version
        if version is None:
            step(f"looking up latest registered version of '{model_name}'")
            version = resolve_latest_version(tracking_uri, model_name)
            step(f"latest version: {version}")

        step(f"promoting v{version} to @champion")
        run([sys.executable, "-m", "src.services.registry",
             "promote", "--version", str(version)],
            cwd=ML_DIR)

        # ── Reload ml-service ────────────────────────────────────────────────
        if args.restart:
            step("rolling out ml-service to pick up new champion")
            run([*kubectl(namespace), "rollout", "restart", "deployment/ml-service"])
            run([*kubectl(namespace), "rollout", "status",
                 "deployment/ml-service", "--timeout=180s"])
        else:
            step("hot-reloading each ml-service pod")
            pods = run([*kubectl(namespace), "get", "pods",
                        "-l", "app=ml-service", "-o", "name"], capture=True).stdout
            pod_names = [p.strip() for p in pods.splitlines() if p.strip()]
            if not pod_names:
                fail("no ml-service pods found")
            for pod in pod_names:
                print(f"    {pod} ... ", end="", flush=True)
                rc = subprocess.call(
                    [*kubectl(namespace), "exec", pod, "--",
                     "curl", "-sf", "-X", "POST",
                     f"http://localhost:{api_port}/api/v1/reload"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                print("ok" if rc == 0 else "FAILED (try --restart)")

        # ── Verify ───────────────────────────────────────────────────────────
        step("verifying loaded model")
        run([*kubectl(namespace), "exec", "deployment/ml-service", "--",
             "curl", "-s", f"http://localhost:{api_port}/api/v1/model-info"])
        print()
        step("done.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        fail("interrupted")
    except subprocess.CalledProcessError as e:
        fail(f"command failed (exit {e.returncode}): {' '.join(e.cmd)}")
