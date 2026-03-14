from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import requests


# =========================
# CONFIGURACIÓN DEL SISTEMA
# =========================
LAT = 40.4168          # Madrid
LON = -3.7038
TIMEZONE = "Europe/Madrid"

YEAR = 2025
START_DATE = f"{YEAR}-01-01"
END_DATE = f"{YEAR}-12-31"

PEAK_POWER_KWP = 1.0   # potencia pico del sistema
TILT = 30              # grados
AZIMUTH = 0            # Open-Meteo: 0 = sur, -90 = este, 90 = oeste
SYSTEM_LOSSES = 0.14   # 14%
TEMP_COEFF = -0.004    # cambio relativo de potencia por °C
NOCT = 45.0            # temperatura nominal de operación aproximada


def fetch_open_meteo_15min() -> pd.DataFrame:
    """
    Descarga para 2025 datos a 15 min de Open-Meteo:
    - global_tilted_irradiance
    - temperature_2m

    Se usa el histórico archivado.
    """
    url = "https://historical-forecast-api.open-meteo.com/v1/forecast"

    params = {
        "latitude": LAT,
        "longitude": LON,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "timezone": TIMEZONE,
        "minutely_15": "global_tilted_irradiance,temperature_2m",
        "tilt": TILT,
        "azimuth": AZIMUTH,
    }

    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()

    if "minutely_15" not in data:
        raise RuntimeError("La respuesta no contiene 'minutely_15'.")

    m15 = data["minutely_15"]

    df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(m15["time"]),
            "gti_w_m2": pd.to_numeric(m15["global_tilted_irradiance"], errors="coerce"),
            "temperature_2m_c": pd.to_numeric(m15["temperature_2m"], errors="coerce"),
        }
    )

    return df


def estimate_cell_temperature(temp_air_c: pd.Series, gti_w_m2: pd.Series, noct: float = NOCT) -> pd.Series:
    """
    Modelo simple de temperatura de célula a partir de NOCT:
    Tcell = Tair + (NOCT - 20) / 800 * GTI
    """
    return temp_air_c + ((noct - 20.0) / 800.0) * gti_w_m2


def estimate_pv_power(
    df: pd.DataFrame,
    peak_power_kwp: float = PEAK_POWER_KWP,
    system_losses: float = SYSTEM_LOSSES,
    temp_coeff: float = TEMP_COEFF,
) -> pd.DataFrame:
    """
    Estima potencia y energía fotovoltaica cada 15 minutos.
    Hipótesis:
    - Producción proporcional a GTI / 1000
    - Corrección térmica simple
    - Pérdidas globales del sistema
    """
    out = df.copy()

    # Temperatura de célula estimada
    out["cell_temperature_c"] = estimate_cell_temperature(
        out["temperature_2m_c"], out["gti_w_m2"]
    )

    # Factor por irradiancia
    irradiance_factor = out["gti_w_m2"] / 1000.0

    # Factor térmico
    temp_factor = 1.0 + temp_coeff * (out["cell_temperature_c"] - 25.0)

    # Evitar valores negativos por temperatura extrema
    temp_factor = temp_factor.clip(lower=0)

    # Potencia DC simplificada y pérdidas globales
    out["pv_power_kw"] = peak_power_kwp * irradiance_factor * temp_factor * (1.0 - system_losses)

    # No puede haber potencia negativa
    out["pv_power_kw"] = out["pv_power_kw"].clip(lower=0)

    # Energía en cada intervalo de 15 minutos
    out["pv_energy_kwh_15min"] = out["pv_power_kw"] * 0.25

    return out


def main():
    project_root = Path(__file__).resolve().parents[1]
    output_dir = project_root / "data"
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_df = fetch_open_meteo_15min()
    result_df = estimate_pv_power(raw_df)

    output_file = output_dir / f"madrid_pv_{YEAR}_15min_1kwp.csv"
    result_df.to_csv(output_file, index=False)

    total_energy = result_df["pv_energy_kwh_15min"].sum()

    print("Descarga y cálculo completados.")
    print(f"Filas: {len(result_df):,}")
    print(f"Energía anual estimada: {total_energy:,.2f} kWh para {PEAK_POWER_KWP} kWp")
    print(f"Guardado en: {output_file}")


if __name__ == "__main__":
    main()