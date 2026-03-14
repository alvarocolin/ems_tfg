from __future__ import annotations

import numpy as np
import pandas as pd


def run_s0(df_input: pd.DataFrame) -> pd.DataFrame:
    """
    Baseline S0: operation without battery.
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

        # PV covers load first
        pv_to_load = min(load[t], pv[t])
        PVuse[t] = pv_to_load

        remaining_load = load[t] - pv_to_load
        excess_pv = pv[t] - pv_to_load

        # Charge battery with excess PV
        energy_room_kwh = max(0.0, (soc_max - soc) * E_kWh)
        max_charge_by_soc_kw = energy_room_kwh / (eta_c * dt_h) if dt_h > 0 else 0.0
        charge_kw = min(excess_pv, Pc_max, max_charge_by_soc_kw)

        Pc[t] = charge_kw
        soc += (eta_c * charge_kw * dt_h) / E_kWh

        PVcurt[t] = excess_pv - charge_kw

        # Discharge battery if load remains
        available_energy_kwh = max(0.0, (soc - soc_res) * E_kWh)
        max_discharge_by_soc_kw = (available_energy_kwh * eta_d) / dt_h if dt_h > 0 else 0.0
        discharge_kw = min(remaining_load, Pd_max, max_discharge_by_soc_kw)

        Pd[t] = discharge_kw
        soc -= (discharge_kw * dt_h) / (eta_d * E_kWh)

        Pg[t] = remaining_load - discharge_kw

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


def run_s2(df_input: pd.DataFrame, params: dict, dt_h: float) -> pd.DataFrame:
    """
    Baseline S2: price-based battery dispatch.

    Logic:
    1. PV covers load first
    2. Excess PV charges battery
    3. If price is low, battery may charge from grid
    4. If price is high, battery may discharge to reduce grid import
    5. Always respect SOC reserve and power limits
    """
    n = len(df_input)

    load = df_input["load_kw"].to_numpy()
    pv = df_input["pv_kw"].to_numpy()
    price = df_input["price_eur_per_kwh"].to_numpy()

    E_kWh = params["E_kWh"]
    Pc_max = params["Pc_max"]
    Pd_max = params["Pd_max"]
    eta_c = params["eta_c"]
    eta_d = params["eta_d"]
    soc_min = params["soc_min"]
    soc_max = params["soc_max"]
    soc_res = params["soc_res"]
    soc_init = params["soc_init"]

    # Price thresholds
    p_low = np.quantile(price, 0.33)
    p_high = np.quantile(price, 0.66)

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

        total_charge_kw = 0.0

        # Available room in battery
        energy_room_kwh = max(0.0, (soc_max - soc) * E_kWh)
        max_charge_by_soc_kw = energy_room_kwh / (eta_c * dt_h) if dt_h > 0 else 0.0

        # 2) First: charge with excess PV
        charge_from_pv_kw = min(excess_pv, Pc_max, max_charge_by_soc_kw)
        total_charge_kw += charge_from_pv_kw

        # Remaining charge headroom
        remaining_pc_headroom = max(0.0, Pc_max - total_charge_kw)

        # Update available room after PV charge
        energy_room_kwh_after_pv = max(
            0.0,
            energy_room_kwh - eta_c * charge_from_pv_kw * dt_h
        )
        max_grid_charge_by_soc_kw = (
            energy_room_kwh_after_pv / (eta_c * dt_h) if dt_h > 0 else 0.0
        )

        # 3) If price is low, optionally charge from grid
        charge_from_grid_kw = 0.0
        if price[t] <= p_low:
            charge_from_grid_kw = min(
                remaining_pc_headroom,
                max_grid_charge_by_soc_kw
            )
            total_charge_kw += charge_from_grid_kw

        # Update SOC after total charging
        Pc[t] = total_charge_kw
        soc += (eta_c * total_charge_kw * dt_h) / E_kWh

        # Curtail only what PV could not send to load or battery
        PVcurt[t] = excess_pv - charge_from_pv_kw

        # 4) If price is high, discharge battery to reduce grid import
        discharge_kw = 0.0
        available_energy_kwh = max(0.0, (soc - soc_res) * E_kWh)
        max_discharge_by_soc_kw = (available_energy_kwh * eta_d) / dt_h if dt_h > 0 else 0.0

        if price[t] >= p_high:
            discharge_kw = min(remaining_load, Pd_max, max_discharge_by_soc_kw)

        Pd[t] = discharge_kw
        soc -= (discharge_kw * dt_h) / (eta_d * E_kWh)

        # 5) Grid import covers remaining load + any charge from grid
        Pg[t] = remaining_load - discharge_kw + charge_from_grid_kw

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