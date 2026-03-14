from __future__ import annotations

import numpy as np
import pandas as pd


def run_s0(df_input: pd.DataFrame) -> pd.DataFrame:
    """
    Baseline S0: operation without battery.

    Logic:
    - PV is used first to cover the load
    - remaining load is imported from the grid
    - excess PV is curtailed
    - no battery charging/discharging
    """
    load = df_input["load_kw"].to_numpy()
    pv = df_input["pv_kw"].to_numpy()

    pv_use = np.minimum(load, pv)
    pg = load - pv_use
    pv_curt = pv - pv_use

    results = pd.DataFrame({
        "timestamp": df_input["timestamp"],
        "Pg": pg,
        "Pc": np.zeros(len(df_input)),
        "Pd": np.zeros(len(df_input)),
        "PVuse": pv_use,
        "PVcurt": pv_curt,
        "SOC": np.full(len(df_input), np.nan),
    })

    return results


def run_s1(df_input: pd.DataFrame, params: dict, dt_h: float) -> pd.DataFrame:
    """
    Baseline S1: maximum self-consumption with battery.

    Logic per timestep:
    1. Use PV to cover load
    2. Charge battery with excess PV
    3. If load still remains, discharge battery (respecting reserve)
    4. Import the rest from the grid
    """
    n = len(df_input)

    load = df_input["load_kw"].to_numpy()
    pv = df_input["pv_kw"].to_numpy()

    E_kWh = params["E_kWh"]
    Pc_max = params["Pc_max"]
    Pd_max = params["Pd_max"]
    eta_c = params["eta_c"]
    eta_d = params["eta_d"]
    soc_min = params["soc_min"]
    soc_max = params["soc_max"]
    soc_res = params["soc_res"]
    soc_init = params["soc_init"]

    Pg = np.zeros(n)
    Pc = np.zeros(n)
    Pd = np.zeros(n)
    PVuse = np.zeros(n)
    PVcurt = np.zeros(n)
    SOC = np.zeros(n)

    soc = soc_init

    for t in range(n):
        SOC[t] = soc

        # 1) PV covers load first
        pv_to_load = min(load[t], pv[t])
        PVuse[t] = pv_to_load

        remaining_load = load[t] - pv_to_load
        excess_pv = pv[t] - pv_to_load

        # 2) Charge battery with excess PV
        energy_room_kwh = max(0.0, (soc_max - soc) * E_kWh)
        max_charge_by_soc_kw = energy_room_kwh / (eta_c * dt_h) if dt_h > 0 else 0.0
        charge_kw = min(excess_pv, Pc_max, max_charge_by_soc_kw)

        Pc[t] = charge_kw

        # SOC increase due to charge
        soc += (eta_c * charge_kw * dt_h) / E_kWh

        # Remaining excess PV after charging is curtailed
        PVcurt[t] = excess_pv - charge_kw

        # 3) If load remains, discharge battery
        available_energy_kwh = max(0.0, (soc - soc_res) * E_kWh)
        max_discharge_by_soc_kw = (available_energy_kwh * eta_d) / dt_h if dt_h > 0 else 0.0
        discharge_kw = min(remaining_load, Pd_max, max_discharge_by_soc_kw)

        Pd[t] = discharge_kw

        # SOC decrease due to discharge
        soc -= (discharge_kw * dt_h) / (eta_d * E_kWh)

        # 4) Import the rest from the grid
        Pg[t] = remaining_load - discharge_kw

        # Numerical protection
        soc = min(max(soc, soc_min), soc_max)

    results = pd.DataFrame({
        "timestamp": df_input["timestamp"],
        "Pg": Pg,
        "Pc": Pc,
        "Pd": Pd,
        "PVuse": PVuse,
        "PVcurt": PVcurt,
        "SOC": SOC,
    })

    return results