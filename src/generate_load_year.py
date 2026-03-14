from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd


def seasonal_factor(day_of_year: np.ndarray, peak_day: int = 200) -> np.ndarray:
    """
    Smooth annual seasonality factor between 0 and 1.
    Peak around day 200 (mid-July), useful for cooling load.
    """
    return 0.5 * (1.0 + np.cos(2 * np.pi * (day_of_year - peak_day) / 365.0))


def generate_load_series(index: pd.DatetimeIndex, seed: int = 123) -> np.ndarray:
    """
    Synthetic data-center load series (kW).

    Logic:
    - 24/7 IT baseload
    - moderate daily variation
    - summer cooling increases auxiliary load
    - small random noise
    """
    rng = np.random.default_rng(seed)

    day_of_year = index.dayofyear.values
    hour = index.hour + index.minute / 60.0

    # 1) IT baseload (main CPD demand)
    base_it = 760.0  # kW

    # 2) Small daily operational variation
    # Slightly higher activity during daytime, but still very flat overall
    daily = 25.0 * np.sin(2 * np.pi * (hour - 8) / 24.0)

    # 3) Cooling load
    # Stronger in summer and mainly during daytime
    sf = seasonal_factor(day_of_year, peak_day=200)  # stronger in July
    daytime_cooling_profile = np.clip(np.sin(np.pi * (hour - 8) / 12.0), 0, None)
    cooling = (40.0 + 80.0 * sf) * daytime_cooling_profile

    # 4) Weekly effect: weekends slightly lighter
    weekend = np.where(index.dayofweek >= 5, -10.0, 0.0)

    # 5) Small random noise
    noise = rng.normal(0.0, 6.0, len(index))

    load = base_it + daily + cooling + weekend + noise
    load = np.clip(load, 700.0, 980.0)

    return np.round(load, 2)


def main() -> None:
    # Build full-year 15-minute index
    index = pd.date_range(
        start="2025-01-01 00:00",
        end="2025-12-31 23:45",
        freq="15min",
    )

    load_kw = generate_load_series(index)

    df = pd.DataFrame({
        "timestamp": index,
        "load_kw": load_kw,
    })

    project_root = Path(__file__).resolve().parents[1]
    output_path = project_root / "data" / "load_year_2025.csv"

    df.to_csv(output_path, index=False)

    print(f"✅ Carga anual guardada en: {output_path}")
    print(df.head())
    print("\nResumen:")
    print(df["load_kw"].describe())


if __name__ == "__main__":
    main()