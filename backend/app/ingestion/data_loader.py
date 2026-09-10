"""Dataset-agnostic data loader interface (CONTRACT.md Section 2: anomaly
detection must work through a dataset-agnostic loader interface).

A DatasetLoader exposes:
  - df            -> pandas DataFrame with a parsed datetime index
  - tags          -> list of sensor/actuator column names (excluding label cols)
  - numeric_array -> (n_rows, n_tags) float32 matrix for fast slicing
  - label_info    -> dict describing ground-truth label column, if any
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np
import pandas as pd


class DatasetLoader(ABC):
    """Base interface every dataset backend must implement."""

    @abstractmethod
    def load(self) -> "LoadedDataset": ...


class LoadedDataset:
    def __init__(self, df: pd.DataFrame, label_column: str | None,
                 label_values: dict[str, int] | None, source_name: str):
        self.df = df
        self.label_column = label_column
        self.label_values = label_values or {}
        self.source_name = source_name

    @property
    def tags(self) -> list[str]:
        return list(self.df.columns)

    @property
    def numeric_array(self) -> np.ndarray:
        return self.df.to_numpy(dtype=np.float32)

    def series(self, tag: str) -> np.ndarray:
        return self.df[tag].to_numpy(dtype=np.float32)

    def __len__(self) -> int:
        return len(self.df)


class SwatAttackLoader(DatasetLoader):
    """Loader for the SWaT attack.csv export (all rows labeled 'Attack')."""

    TIMESTAMP_FORMAT = "%d/%m/%Y %I:%M:%S %p"

    def __init__(self, csv_path: str | Path):
        self.csv_path = Path(csv_path)
        if not self.csv_path.exists():
            raise FileNotFoundError(
                f"Dataset not found at {self.csv_path}. Place attack.csv in "
                "backend/data/ (see README)."
            )

    def load(self) -> LoadedDataset:
        raw = pd.read_csv(self.csv_path)
        raw.columns = [c.strip() for c in raw.columns]

        label_column = None
        for candidate in ("Normal/Attack", "Label", "label", "attack"):
            if candidate in raw.columns:
                label_column = candidate
                break

        ts_col = raw.columns[0]  # first column is the timestamp in SWaT exports
        timestamps = pd.to_datetime(
            raw[ts_col].astype(str).str.strip(),
            format=self.TIMESTAMP_FORMAT,
            errors="coerce",
        )
        if timestamps.isna().any():
            # Fallback for datasets that deviate from the SWaT format.
            timestamps = pd.to_datetime(
                raw[ts_col].astype(str).str.strip(), errors="coerce"
            )

        df = raw.drop(columns=[ts_col]).apply(pd.to_numeric, errors="coerce")
        df = df.ffill().fillna(0)
        df.index = timestamps
        df.index.name = "timestamp"

        label_values: dict[str, int] = {}
        if label_column is not None:
            counts = raw[label_column].astype(str).str.strip().value_counts()
            label_values = {str(k): int(v) for k, v in counts.items()}

        return LoadedDataset(
            df=df,
            label_column=label_column,
            label_values=label_values,
            source_name=self.csv_path.name,
        )


def load_default_dataset() -> LoadedDataset:
    """Load the demo dataset from backend/data/attack.csv."""
    default_path = Path(__file__).resolve().parents[2] / "data" / "attack.csv"
    return SwatAttackLoader(default_path).load()
