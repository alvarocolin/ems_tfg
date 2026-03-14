from __future__ import annotations

import pandas as pd


def compute_kpis(
    df_input: pd.DataFrame,
    df_result: pd.DataFrame,
    dt_h: float,
    e_kwh: float | None = None,
    c_deg: float = 0.0,
) -> dict:
    grid_cost_eur = (df_input["price_eur_per_kwh"] * df_result["Pg"] * dt_h).sum()

    discharged_energy_kwh = (df_result["Pd"] * dt_h).sum()
    degradation_cost_eur = c_deg * discharged_energy_kwh
    total_cost_eur = grid_cost_eur + degradation_cost_eur

    total_pv = df_input["pv_kw"].sum()
    total_pv_use = df_result["PVuse"].sum()
    autocons_pct = (total_pv_use / total_pv * 100.0) if total_pv > 0 else 0.0

    total_pv_curt_kwh = (df_result["PVcurt"] * dt_h).sum()
    grid_energy_kwh = (df_result["Pg"] * dt_h).sum()
    grid_power_peak_kw = df_result["Pg"].max()

    cycles_eq = None
    if e_kwh is not None and e_kwh > 0:
        cycles_eq = discharged_energy_kwh / e_kwh

    return {
        "grid_cost_eur": float(grid_cost_eur),
        "degradation_cost_eur": float(degradation_cost_eur),
        "total_cost_eur": float(total_cost_eur),
        "grid_energy_kwh": float(grid_energy_kwh),
        "grid_power_peak_kw": float(grid_power_peak_kw),
        "autocons_pct": float(autocons_pct),
        "pv_curtailment_kwh": float(total_pv_curt_kwh),
        "discharged_energy_kwh": float(discharged_energy_kwh),
        "cycles_eq": None if cycles_eq is None else float(cycles_eq),
    }