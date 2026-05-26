"""
Path configuration for the project.

All directory and file paths are defined here as Pydantic settings.
Directories are auto-created on instantiation.
"""

from pathlib import Path
from pydantic import BaseModel, model_validator


class PathConfig(BaseModel):
    """Project directory and file path configuration."""

    project_root: Path = Path(__file__).resolve().parent.parent.parent

    # Data directories
    data_dir: Path = None
    raw_data_dir: Path = None
    processed_data_dir: Path = None
    artifacts_dir: Path = None

    # Data files
    raw_data_file: str = None  # Auto-detected from data/raw/
    processed_features_file: str = "features.parquet"

    @model_validator(mode="after")
    def set_derived_paths(self):
        if self.data_dir is None:
            self.data_dir = self.project_root / "data"
        if self.raw_data_dir is None:
            self.raw_data_dir = self.data_dir / "raw"
        if self.processed_data_dir is None:
            self.processed_data_dir = self.data_dir / "processed"
        if self.artifacts_dir is None:
            self.artifacts_dir = self.project_root / "artifacts"
        return self

    def ensure_dirs(self):
        """Create all directories if they don't exist."""
        for d in [self.raw_data_dir, self.processed_data_dir, self.artifacts_dir]:
            d.mkdir(parents=True, exist_ok=True)

    @property
    def raw_data_filepath(self) -> Path:
        # If explicitly set, use it
        if self.raw_data_file:
            return self.raw_data_dir / self.raw_data_file
        # Auto-detect: find first CSV matching Real_Estate_Sales*
        candidates = sorted(self.raw_data_dir.glob("Real_Estate_Sales*.csv"))
        if candidates:
            return candidates[0]
        # Fallback: any CSV in raw/
        all_csv = sorted(self.raw_data_dir.glob("*.csv"))
        if all_csv:
            return all_csv[0]
        raise FileNotFoundError(f"No CSV file found in {self.raw_data_dir}")

    @property
    def processed_features_filepath(self) -> Path:
        return self.processed_data_dir / self.processed_features_file


# Default singleton instance
path_config = PathConfig()
path_config.ensure_dirs()
