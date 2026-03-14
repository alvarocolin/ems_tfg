from __future__ import annotations

from pathlib import Path
import pandas as pd

from data_loader import load_input_data, infer_timestep_hours
from kpis import compute_kpis
from plots import (
    plot_load_pv_grid,
    plot_soc,
    plot_bar_costs,
    plot_bar_autocons,
    plot_bar_cycles,
    plot_bar_peak_grid,
    plot_dispatch_detail,
)


def build_summary_table(
    df_input: pd.DataFrame,
    results_map: dict[str, pd.DataFrame],
    dt_h: float,
    e_kwh: float,
    c_deg: float,
) -> pd.DataFrame:
    """
    Build KPI summary table for all strategies.
    """
    rows = []

    for strategy, df_result in results_map.items():
        kpis = compute_kpis(
            df_input=df_input,
            df_result=df_result,
            dt_h=dt_h,
            e_kwh=e_kwh,
            c_deg=c_deg,
        )

        row = {"strategy": strategy}
        row.update(kpis)
        rows.append(row)

    df_summary = pd.DataFrame(rows)
    return df_summary


def run_analysis(project_root: str | Path, params: dict) -> None:
    project_root = Path(project_root)

    data_path = project_root / "data" / "input_day.csv"
    results_dir = project_root / "results"
    tables_dir = results_dir / "tables"
    figures_dir = results_dir / "figures"

    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    # Load input
    df_input = load_input_data(data_path)
    dt_h = infer_timestep_hours(df_input)

    # Load results
    df_s0 = pd.read_csv(results_dir / "s0_results.csv", parse_dates=["timestamp"])
    df_s1 = pd.read_csv(results_dir / "s1_results.csv", parse_dates=["timestamp"])
    df_s2 = pd.read_csv(results_dir / "s2_results.csv", parse_dates=["timestamp"])
    df_s3 = pd.read_csv(results_dir / "s3_results.csv", parse_dates=["timestamp"])

    results_map = {
        "S0": df_s0,
        "S1": df_s1,
        "S2": df_s2,
        "S3": df_s3,
    }

    # Build and save summary table
    df_summary = build_summary_table(
        df_input=df_input,
        results_map=results_map,
        dt_h=dt_h,
        e_kwh=params["E_kWh"],
        c_deg=params["c_deg"],
    )

    summary_path = tables_dir / "summary_kpis.csv"
    df_summary.to_csv(summary_path, index=False)

    # Generate plots per strategy
    plot_load_pv_grid(
        df_input,
        df_s0,
        "S0 - Load / PV / Grid",
        figures_dir / "s0_load_pv_grid.png",
    )

    plot_load_pv_grid(
        df_input,
        df_s1,
        "S1 - Load / PV / Grid",
        figures_dir / "s1_load_pv_grid.png",
    )

    plot_load_pv_grid(
        df_input,
        df_s2,
        "S2 - Load / PV / Grid",
        figures_dir / "s2_load_pv_grid.png",
    )

    plot_load_pv_grid(
        df_input,
        df_s3,
        "S3 - Load / PV / Grid",
        figures_dir / "s3_load_pv_grid.png",
    )

    plot_dispatch_detail(
        df_input,
        df_s2,
        "S2 - Dispatch detail",
        figures_dir / "s2_dispatch_detail.png",
    )

    plot_dispatch_detail(
        df_input,
        df_s3,
        "S3 - Dispatch detail",
        figures_dir / "s3_dispatch_detail.png",
    )

    plot_soc(df_s1, "S1 - Battery SOC", figures_dir / "s1_soc.png")
    plot_soc(df_s2, "S2 - Battery SOC", figures_dir / "s2_soc.png")
    plot_soc(df_s3, "S3 - Battery SOC", figures_dir / "s3_soc.png")

    plot_bar_costs(df_summary, figures_dir / "bar_total_cost.png")
    plot_bar_autocons(df_summary, figures_dir / "bar_autocons.png")
    plot_bar_cycles(df_summary, figures_dir / "bar_cycles.png")
    plot_bar_peak_grid(df_summary, figures_dir / "bar_peak_grid.png")

    print("✅ Analysis completed")
    print(f"Tabla resumen guardada en: {summary_path}")
    print(f"Figuras guardadas en: {figures_dir}")