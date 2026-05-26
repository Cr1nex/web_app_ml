"""
MLflow Model Registry management.

Provides CLI commands to manage the model lifecycle:
    - List all registered model versions
    - Promote a model from staging to production (champion)
    - Compare model versions side-by-side
    - Archive old versions

Usage:
    python -m src.services.registry list
    python -m src.services.registry promote --version 3
    python -m src.services.registry compare --versions 1 2 3
    python -m src.services.registry archive --version 1
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

import mlflow
from mlflow import MlflowClient
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import MLFLOW_TRACKING_URI, MODEL_NAME

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(levelname)s — %(message)s")
logger = logging.getLogger(__name__)


def get_client() -> MlflowClient:
    """Create an MLflow client with configured tracking URI."""
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    return MlflowClient(MLFLOW_TRACKING_URI)


def list_versions(model_name: str = MODEL_NAME):
    """
    List all versions of the registered model with their aliases and metrics.
    """
    client = get_client()

    try:
        versions = client.search_model_versions(f"name='{model_name}'")
    except Exception:
        logger.warning(f"No registered model found with name '{model_name}'")
        return

    if not versions:
        logger.warning(f"No versions found for model '{model_name}'")
        return

    # Get aliases for this model
    registered_model = client.get_registered_model(model_name)
    alias_map = {}
    if hasattr(registered_model, "aliases"):
        for alias, version in registered_model.aliases.items():
            alias_map.setdefault(version, []).append(alias)

    logger.info(f"Model: {model_name} — Total versions: {len(versions)}")

    rows = []
    for v in sorted(versions, key=lambda x: int(x.version), reverse=True):
        aliases = alias_map.get(v.version, [])
        alias_str = ", ".join(f"@{a}" for a in aliases) if aliases else "—"

        # Get metrics from the source run
        metrics_str = "—"
        if v.run_id:
            try:
                run = client.get_run(v.run_id)
                mae = run.data.metrics.get("val_mae", run.data.metrics.get("test_mae"))
                rmse = run.data.metrics.get("val_rmse", run.data.metrics.get("test_rmse"))
                r2 = run.data.metrics.get("val_r2", run.data.metrics.get("test_r2"))
                parts = []
                if mae is not None:
                    parts.append(f"MAE=${mae:,.0f}")
                if rmse is not None:
                    parts.append(f"RMSE=${rmse:,.0f}")
                if r2 is not None:
                    parts.append(f"R²={r2:.4f}")
                metrics_str = " | ".join(parts) if parts else "—"
            except Exception:
                pass

        rows.append({
            "Version": v.version,
            "Aliases": alias_str,
            "Status": v.status,
            "Run ID": v.run_id[:8] if v.run_id else "—",
            "Metrics": metrics_str,
            "Created": str(v.creation_timestamp),
        })

    df = pd.DataFrame(rows)
    logger.info(f"Registered model versions:\n{df.to_string(index=False)}")

    return versions


def promote_to_production(version: int, model_name: str = MODEL_NAME):
    """
    Promote a model version to production by setting the 'champion' alias.

    This also sets the 'production' alias for backward compatibility
    and removes the 'staging' alias if present on this version.
    """
    client = get_client()
    version_str = str(version)

    # Verify the version exists
    try:
        model_version = client.get_model_version(model_name, version_str)
    except Exception:
        logger.error(f"Version {version} not found for model '{model_name}'")
        return

    # Set champion alias (MLflow 2.x recommended approach)
    client.set_registered_model_alias(model_name, "champion", version_str)
    logger.info(f"Set alias @champion → version {version}")

    # Also set 'production' alias for backward compatibility
    client.set_registered_model_alias(model_name, "production", version_str)
    logger.info(f"Set alias @production → version {version}")

    logger.info(
        f"Model '{model_name}' v{version} promoted to PRODUCTION — "
        f"Aliases: @champion, @production — Run ID: {model_version.run_id}"
    )
    logger.info(f"Load with: mlflow.pyfunc.load_model('models:/{model_name}@champion')")
    logger.info(f"Serve with: mlflow models serve -m 'models:/{model_name}@champion' -p 5002 --no-conda")

    return model_version


def compare_versions(versions: List[int], model_name: str = MODEL_NAME):
    """
    Compare metrics across multiple model versions side-by-side.
    """
    client = get_client()

    rows = []
    for v in versions:
        try:
            mv = client.get_model_version(model_name, str(v))
            run = client.get_run(mv.run_id)

            row = {"Version": v, "Run ID": mv.run_id[:8]}

            # Extract all logged params
            for key in ["model_type", "max_depth", "learning_rate", "n_estimators"]:
                row[key] = run.data.params.get(key, "—")

            # Extract all logged metrics
            for key in ["val_mae", "val_rmse", "val_r2", "test_mae", "test_rmse", "test_r2"]:
                val = run.data.metrics.get(key)
                if val is not None:
                    if "mae" in key or "rmse" in key:
                        row[key] = f"${val:,.0f}"
                    else:
                        row[key] = f"{val:.4f}"
                else:
                    row[key] = "—"

            rows.append(row)

        except Exception as e:
            logger.warning(f"Could not load version {v}: {e}")

    if rows:
        df = pd.DataFrame(rows)
        logger.info(f"Model Comparison — {model_name}:\n{df.to_string(index=False)}")

    return rows


def archive_version(version: int, model_name: str = MODEL_NAME):
    """
    Archive a model version by removing all its aliases
    and adding a descriptive tag.
    """
    client = get_client()
    version_str = str(version)

    # Check if this version has any aliases
    registered_model = client.get_registered_model(model_name)
    if hasattr(registered_model, "aliases"):
        for alias, alias_version in registered_model.aliases.items():
            if alias_version == version_str:
                client.delete_registered_model_alias(model_name, alias)
                logger.info(f"Removed alias @{alias} from version {version}")

    # Tag the version as archived
    client.set_model_version_tag(model_name, version_str, "status", "archived")

    logger.info(f"Model '{model_name}' v{version} archived — all aliases removed, tagged as archived")


def stage_to_staging(version: int, model_name: str = MODEL_NAME):
    """
    Set a model version to staging stage.
    """
    client = get_client()
    version_str = str(version)

    try:
        client.get_model_version(model_name, version_str)
    except Exception:
        logger.error(f"Version {version} not found for model '{model_name}'")
        return

    client.set_registered_model_alias(model_name, "staging", version_str)
    logger.info(f"Model '{model_name}' v{version} set to STAGING — Alias: @staging")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MLflow Model Registry Management")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # list
    list_parser = subparsers.add_parser("list", help="List all model versions")
    list_parser.add_argument("--model", default=MODEL_NAME)

    # promote
    promote_parser = subparsers.add_parser("promote", help="Promote version to production")
    promote_parser.add_argument("--version", type=int, required=True)
    promote_parser.add_argument("--model", default=MODEL_NAME)

    # staging
    staging_parser = subparsers.add_parser("staging", help="Set version to staging")
    staging_parser.add_argument("--version", type=int, required=True)
    staging_parser.add_argument("--model", default=MODEL_NAME)

    # compare
    compare_parser = subparsers.add_parser("compare", help="Compare model versions")
    compare_parser.add_argument("--versions", type=int, nargs="+", required=True)
    compare_parser.add_argument("--model", default=MODEL_NAME)

    # archive
    archive_parser = subparsers.add_parser("archive", help="Archive a model version")
    archive_parser.add_argument("--version", type=int, required=True)
    archive_parser.add_argument("--model", default=MODEL_NAME)

    args = parser.parse_args()

    if args.command == "list":
        list_versions(args.model)
    elif args.command == "promote":
        promote_to_production(args.version, args.model)
    elif args.command == "staging":
        stage_to_staging(args.version, args.model)
    elif args.command == "compare":
        compare_versions(args.versions, args.model)
    elif args.command == "archive":
        archive_version(args.version, args.model)
    else:
        parser.print_help()
