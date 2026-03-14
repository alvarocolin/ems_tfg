from __future__ import annotations

import pandas as pd


def compute_kpis(
    df_input: pd.DataFrame,
    df_result: pd.DataFrame,
    dt_h: float,
    e_kwh: float | None = None,
) -> dict:
    """
    Compute basic KPIs for a simulation result.
    """
    cost_eur = (df_input["price_eur_per_kwh"] * df_result["Pg"] * dt_h).sum()

    total_pv = df_input["pv_kw"].sum()
    total_pv_use = df_result["PVuse"].sum()
    autocons_pct = (total_pv_use / total_pv * 100.0) if total_pv > 0 else 0.0

    discharged_energy_kwh = (df_result["Pd"] * dt_h).sum()

    cycles_eq = None
    if e_kwh is not None and e_kwh > 0:
        cycles_eq = discharged_energy_kwh / e_kwh

    return {
        "cost_eur": float(cost_eur),
        "autocons_pct": float(autocons_pct),
        "discharged_energy_kwh": float(discharged_energy_kwh),
        "cycles_eq": None if cycles_eq is None else float(cycles_eq),
    }