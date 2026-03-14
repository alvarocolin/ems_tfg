from __future__ import annotations

from pathlib import Path
import pandas as pd


REQUIRED_COLUMNS = ["timestamp", "load_kw", "pv_kw", "price_eur_per_kwh"]


def load_input_data(csv_path: str | Path) -> pd.DataFrame:
    """
    Load and validate input time series for the EMS simulation.

    Expected columns:
    - timestamp
    - load_kw
    - pv_kw
    - price_eur_per_kwh
    """
    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {csv_path}")

    df = pd.read_csv(csv_path, parse_dates=["timestamp"])

    # Check required columns
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(
            f"Faltan columnas obligatorias en el CSV: {missing_cols}"
        )

    # Drop duplicate timestamps
    if df["timestamp"].duplicated().any():
        raise ValueError("Hay timestamps duplicados en el archivo de entrada.")

    # Sort by timestamp just in case
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Check nulls
    if df[REQUIRED_COLUMNS].isnull().any().any():
        raise ValueError("Hay valores nulos en las columnas obligatorias.")

    # Check non-negative values
    numeric_cols = ["load_kw", "pv_kw", "price_eur_per_kwh"]
    for col in numeric_cols:
        if (df[col] < 0).any():
            raise ValueError(f"La columna '{col}' contiene valores negativos.")

    # Check time step consistency
    time_diffs = df["timestamp"].diff().dropna()
    if not time_diffs.empty and time_diffs.nunique() > 1:
        raise ValueError(
            "Los intervalos temporales no son uniformes. Revisa el CSV."
        )

    return df


def infer_timestep_hours(df: pd.DataFrame) -> float:
    """
    Infer the timestep in hours from the timestamp column.
    """
    if len(df) < 2:
        raise ValueError("No hay suficientes filas para inferir el paso temporal.")

    delta = df["timestamp"].iloc[1] - df["timestamp"].iloc[0]
    return delta.total_seconds() / 3600.0