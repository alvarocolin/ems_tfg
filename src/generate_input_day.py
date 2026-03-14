from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd


def build_madrid_spring_day() -> pd.DataFrame:
    """
    Synthetic spring day for a Madrid-like location.
    15-minute resolution.
    Daylight roughly 07:30-19:15.
    Load: data-center-like, fairly flat.
    PV: strong enough to exceed load around midday.
    """
    timestamps = pd.date_range(
        start="2026-03-14 00:00",
        end="2026-03-14 23:45",
        freq="15min"
    )

    n = len(timestamps)
    hours = np.array([ts.hour + ts.minute / 60 for ts in timestamps])

    # -------------------------
    # 1) LOAD PROFILE (kW)
    # -------------------------
    # Fairly flat CPD-like load with small daily variation
    # Night: ~790-820 kW
    # Day: ~850-920 kW
    load = (
        830
        + 45 * np.sin((hours - 7) / 24 * 2 * np.pi)
        + 20 * np.sin((hours - 15) / 24 * 4 * np.pi)
    )

    # Add a mild late-afternoon bump typical of cooling / activity
    load += np.where((hours >= 16) & (hours <= 20), 35, 0)

    # Keep within a realistic range
    load = np.clip(load, 780, 920)

    # -------------------------
    # 2) PV PROFILE (kW)
    # -------------------------
    # Madrid-like spring daylight window
    sunrise = 7.5    # 07:30
    sunset = 19.25   # 19:15
    pv_peak = 1200.0 # 1.2 MWp effective AC peak

    pv = np.zeros(n)

    daylight_mask = (hours >= sunrise) & (hours <= sunset)
    x = (hours[daylight_mask] - sunrise) / (sunset - sunrise)  # 0..1

    # Bell-shaped solar production
    pv[daylight_mask] = pv_peak * np.sin(np.pi * x) ** 1.7

    # -------------------------
    # 3) PRICE PROFILE (€/kWh)
    # -------------------------
    price = np.zeros(n)

    for i, h in enumerate(hours):
        if 0 <= h < 8:
            price[i] = 0.11
        elif 8 <= h < 14:
            price[i] = 0.16
        elif 14 <= h < 18:
            price[i] = 0.22
        elif 18 <= h < 22:
            price[i] = 0.27
        else:
            price[i] = 0.14

    df = pd.DataFrame({
        "timestamp": timestamps,
        "load_kw": np.round(load, 2),
        "pv_kw": np.round(pv, 2),
        "price_eur_per_kwh": np.round(price, 3),
    })

    return df


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    output_path = project_root / "data" / "input_day.csv"

    df = build_madrid_spring_day()
    df.to_csv(output_path, index=False)

    print(f"✅ Nuevo input guardado en: {output_path}")
    print(df.head(12))
    print("\nResumen:")
    print(df[["load_kw", "pv_kw", "price_eur_per_kwh"]].describe())

    # Extra check: hours with PV > load
    hours_pv_gt_load = (df["pv_kw"] > df["load_kw"]).sum()
    print(f"\nIntervalos con FV > carga: {hours_pv_gt_load} de {len(df)}")


if __name__ == "__main__":
    main()