from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd


def build_timestamps(year: int = 2025) -> pd.DatetimeIndex:
    """
    Build a full-year 15-minute timestamp index.
    """
    return pd.date_range(
        start=f"{year}-01-01 00:00",
        end=f"{year}-12-31 23:45",
        freq="15min",
    )


def seasonal_factor(day_of_year: np.ndarray, peak_day: int = 172) -> np.ndarray:
    """
    Smooth annual seasonality factor between ~0 and ~1.
    Peak around day 172 (late June).
    """
    return 0.5 * (1.0 + np.cos(2 * np.pi * (day_of_year - peak_day) / 365.0))


def generate_price_series(index: pd.DatetimeIndex, seed: int = 42) -> np.ndarray:
    """
    Synthetic Spain-like quarter-hour electricity price series (€/kWh).

    Logic:
    - lower prices at night
    - higher prices in late afternoon/evening
    - winter/summer seasonality
    - moderate random noise
    - occasional spikes
    """
    rng = np.random.default_rng(seed)

    hour = index.hour + index.minute / 60.0
    month = index.month
    day_of_year = index.dayofyear.values

    # Base monthly level (€/kWh)
    monthly_base = {
        1: 0.13, 2: 0.12, 3: 0.11, 4: 0.10,
        5: 0.10, 6: 0.11, 7: 0.12, 8: 0.13,
        9: 0.12, 10: 0.11, 11: 0.12, 12: 0.14,
    }
    base = np.array([monthly_base[m] for m in month], dtype=float)

    # Intraday pattern
    # cheap at night, moderate midday, expensive late afternoon/evening
    intraday = np.where(
        (hour >= 0) & (hour < 7), -0.02,
        np.where(
            (hour >= 7) & (hour < 14), 0.00,
            np.where(
                (hour >= 14) & (hour < 18), 0.03,
                np.where((hour >= 18) & (hour < 22), 0.06, 0.00)
            )
        )
    )

    # Weekly effect: weekends slightly cheaper
    weekend = np.where(index.dayofweek >= 5, -0.01, 0.0)

    # Seasonal effect: winter a bit more expensive
    winter_boost = np.where((month <= 2) | (month == 12), 0.01, 0.0)

    # Noise
    noise = rng.normal(0.0, 0.008, len(index))

    # Occasional spikes
    spikes = np.zeros(len(index))
    spike_mask = rng.random(len(index)) < 0.003
    spikes[spike_mask] = rng.uniform(0.03, 0.10, spike_mask.sum())

    price = base + intraday + weekend + winter_boost + noise + spikes
    price = np.clip(price, 0.02, 0.35)

    return np.round(price, 4)


def generate_pv_series(index: pd.DatetimeIndex, pv_peak_kw: float = 1200.0) -> np.ndarray:
    """
    Synthetic PV generation for a Spain-like location.

    Logic:
    - daylight duration varies through the year
    - summer has longer days and slightly stronger production
    - bell-shaped daily solar curve
    """
    day_of_year = index.dayofyear.values
    hour = index.hour + index.minute / 60.0

    # Annual factor: stronger in summer, weaker in winter
    sf = seasonal_factor(day_of_year, peak_day=172)  # max around June
    annual_strength = 0.65 + 0.35 * sf

    # Approx sunrise / sunset variation (Spain-like central location)
    sunrise = 8.3 - 1.6 * sf     # winter ~8.3, summer ~6.7
    sunset = 17.6 + 3.2 * sf     # winter ~17.6, summer ~20.8

    pv = np.zeros(len(index))

    daylight = (hour >= sunrise) & (hour <= sunset)
    x = np.zeros(len(index))
    x[daylight] = (hour[daylight] - sunrise[daylight]) / (sunset[daylight] - sunrise[daylight])

    # Bell-like shape
    pv_shape = np.zeros(len(index))
    pv_shape[daylight] = np.sin(np.pi * x[daylight]) ** 1.7

    pv = pv_peak_kw * annual_strength * pv_shape
    pv = np.clip(pv, 0.0, None)

    return np.round(pv, 2)


def generate_load_series(index: pd.DatetimeIndex, seed: int = 123) -> np.ndarray:
    """
    Synthetic data-center load series (kW).

    Logic:
    - 24/7 IT baseload
    - moderate daily variation
    - summer cooling increases auxiliary load
    - small noise
    """
    rng = np.random.default_rng(seed)

    day_of_year = index.dayofyear.values
    hour = index.hour + index.minute / 60.0
    month = index.month

    # IT baseload
    base_it = 760.0

    # Small daily operational variation
    daily = 25.0 * np.sin(2 * np.pi * (hour - 8) / 24.0)

    # Cooling load stronger in summer and daytime
    sf = seasonal_factor(day_of_year, peak_day=200)  # stronger in July
    daytime_cooling_profile = np.clip(np.sin(np.pi * (hour - 8) / 12.0), 0, None)
    cooling = (40.0 + 80.0 * sf) * daytime_cooling_profile

    # Weekly effect: weekends slightly lighter
    weekend = np.where(index.dayofweek >= 5, -10.0, 0.0)

    # Small random noise
    noise = rng.normal(0.0, 6.0, len(index))

    load = base_it + daily + cooling + weekend + noise
    load = np.clip(load, 700.0, 980.0)

    return np.round(load, 2)


def build_year_dataset(year: int = 2025) -> pd.DataFrame:
    index = build_timestamps(year=year)

    df = pd.DataFrame({
        "timestamp": index,
        "load_kw": generate_load_series(index),
        "pv_kw": generate_pv_series(index, pv_peak_kw=1200.0),
        "price_eur_per_kwh": generate_price_series(index),
    })

    return df


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    output_path = project_root / "data" / "input_year.csv"

    df = build_year_dataset(year=2025)
    df.to_csv(output_path, index=False)

    print(f"✅ Dataset anual guardado en: {output_path}")
    print(df.head())
    print("\nResumen:")
    print(df[["load_kw", "pv_kw", "price_eur_per_kwh"]].describe())


if __name__ == "__main__":
    main()