from __future__ import annotations

from pathlib import Path
import pandas as pd

from data_loader import load_input_data, infer_timestep_hours
from baselines import run_s0, run_s1, run_s2
from optimizer import run_s3_optimizer
from kpis import compute_kpis
from plots import (
    plot_sensitivity_cost,
    plot_sensitivity_peak,
    plot_sensitivity_autocons,
)


def run_battery_sensitivity(
    project_root: str | Path,
    base_params: dict,
    e_values_kwh: list[float],
) -> None:
    """
    Run a battery energy capacity sensitivity analysis.

    Option A:
    - Only E_kWh changes
    - Pc_max and Pd_max remain fixed
    """
    project_root = Path(project_root)

    data_path = project_root / "data" / "input_day.csv"
    results_dir = project_root / "results"
    tables_dir = results_dir / "tables"
    figures_dir = results_dir / "figures"

    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    # Load input data
    df_input = load_input_data(data_path)
    dt_h = infer_timestep_hours(df_input)

    rows = []

    # Baseline S0 only once, as reference
    df_s0 = run_s0(df_input)
    kpis_s0 = compute_kpis(
        df_input=df_input,
        df_result=df_s0,
        dt_h=dt_h,
        e_kwh=base_params["E_kWh"],
        c_deg=base_params["c_deg"],
    )

    row_s0 = {
        "scenario": "baseline_no_battery",
        "strategy": "S0",
        "E_kWh": 0.0,
    }
    row_s0.update(kpis_s0)
    rows.append(row_s0)

    # Sensitivity loop for battery energy capacity
    for e_kwh in e_values_kwh:
        params = base_params.copy()
        params["E_kWh"] = e_kwh

        # Option A: keep power limits fixed
        # params["Pc_max"] and params["Pd_max"] are NOT modified

        df_s1 = run_s1(df_input=df_input, params=params, dt_h=dt_h)
        df_s2 = run_s2(df_input=df_input, params=params, dt_h=dt_h)
        df_s3 = run_s3_optimizer(df_input=df_input, params=params, dt_h=dt_h)

        results_map = {
            "S1": df_s1,
            "S2": df_s2,
            "S3": df_s3,
        }

        for strategy, df_result in results_map.items():
            kpis = compute_kpis(
                df_input=df_input,
                df_result=df_result,
                dt_h=dt_h,
                e_kwh=params["E_kWh"],
                c_deg=params["c_deg"],
            )

            row = {
                "scenario": f"E_{int(e_kwh)}kWh",
                "strategy": strategy,
                "E_kWh": float(e_kwh),
            }
            row.update(kpis)
            rows.append(row)

    df_sens = pd.DataFrame(rows)

    # Reference values from S0
    s0_total_cost = df_sens.loc[df_sens["strategy"] == "S0", "total_cost_eur"].iloc[0]
    s0_peak = df_sens.loc[df_sens["strategy"] == "S0", "grid_power_peak_kw"].iloc[0]
    s0_autocons = df_sens.loc[df_sens["strategy"] == "S0", "autocons_pct"].iloc[0]

    # Additional comparison KPIs
    df_sens["cost_savings_vs_s0_eur"] = s0_total_cost - df_sens["total_cost_eur"]
    df_sens["peak_reduction_vs_s0_kw"] = s0_peak - df_sens["grid_power_peak_kw"]
    df_sens["autocons_gain_vs_s0_pct"] = df_sens["autocons_pct"] - s0_autocons

    # Save summary table
    output_table = tables_dir / "battery_sensitivity_kpis.csv"
    df_sens.to_csv(output_table, index=False)

    # Plot only strategies with battery
    df_plot = df_sens[df_sens["strategy"] != "S0"].copy()

    plot_sensitivity_cost(
        df_plot,
        figures_dir / "sens_battery_cost.png",
    )
    plot_sensitivity_peak(
        df_plot,
        figures_dir / "sens_battery_peak.png",
    )
    plot_sensitivity_autocons(
        df_plot,
        figures_dir / "sens_battery_autocons.png",
    )

    print("✅ Battery sensitivity completed")
    print(f"Tabla guardada en: {output_table}")
    print(f"Figuras guardadas en: {figures_dir}")