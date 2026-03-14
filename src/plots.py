from __future__ import annotations

from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd


def plot_load_pv_grid(
    df_input: pd.DataFrame,
    df_result: pd.DataFrame,
    title: str,
    output_path: str | Path,
) -> None:
    """
    Plot load, PV and grid import.
    """
    output_path = Path(output_path)

    plt.figure(figsize=(12, 6))
    plt.plot(df_input["timestamp"], df_input["load_kw"], label="Load (kW)")
    plt.plot(df_input["timestamp"], df_input["pv_kw"], label="PV available (kW)")
    plt.plot(df_result["timestamp"], df_result["Pg"], label="Grid import (kW)")
    plt.xlabel("Time")
    plt.ylabel("Power (kW)")
    plt.title(title)
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def plot_soc(
    df_result: pd.DataFrame,
    title: str,
    output_path: str | Path,
) -> None:
    """
    Plot battery state of charge.
    """
    output_path = Path(output_path)

    if "SOC" not in df_result.columns:
        return

    plt.figure(figsize=(12, 4))
    plt.plot(df_result["timestamp"], df_result["SOC"], label="SOC")
    plt.xlabel("Time")
    plt.ylabel("SOC (-)")
    plt.title(title)
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def plot_bar_costs(
    df_summary: pd.DataFrame,
    output_path: str | Path,
) -> None:
    """
    Bar chart for total cost by strategy.
    """
    output_path = Path(output_path)

    plt.figure(figsize=(8, 5))
    plt.bar(df_summary["strategy"], df_summary["total_cost_eur"])
    plt.xlabel("Strategy")
    plt.ylabel("Total cost (€)")
    plt.title("Total cost by strategy")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def plot_bar_autocons(
    df_summary: pd.DataFrame,
    output_path: str | Path,
) -> None:
    """
    Bar chart for PV self-consumption by strategy.
    """
    output_path = Path(output_path)

    plt.figure(figsize=(8, 5))
    plt.bar(df_summary["strategy"], df_summary["autocons_pct"])
    plt.xlabel("Strategy")
    plt.ylabel("PV self-consumption (%)")
    plt.title("PV self-consumption by strategy")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def plot_bar_cycles(
    df_summary: pd.DataFrame,
    output_path: str | Path,
) -> None:
    """
    Bar chart for equivalent battery cycles by strategy.
    """
    output_path = Path(output_path)

    plt.figure(figsize=(8, 5))
    plt.bar(df_summary["strategy"], df_summary["cycles_eq"])
    plt.xlabel("Strategy")
    plt.ylabel("Equivalent cycles (-)")
    plt.title("Equivalent battery cycles by strategy")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def plot_bar_peak_grid(
    df_summary: pd.DataFrame,
    output_path: str | Path,
) -> None:
    """
    Bar chart for peak grid power by strategy.
    """
    output_path = Path(output_path)

    plt.figure(figsize=(8, 5))
    plt.bar(df_summary["strategy"], df_summary["grid_power_peak_kw"])
    plt.xlabel("Strategy")
    plt.ylabel("Peak grid power (kW)")
    plt.title("Peak grid power by strategy")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def plot_sensitivity_cost(
    df_sens: pd.DataFrame,
    output_path: str | Path,
) -> None:
    output_path = Path(output_path)

    plt.figure(figsize=(8, 5))
    for strategy in sorted(df_sens["strategy"].unique()):
        df_aux = df_sens[df_sens["strategy"] == strategy].sort_values("E_kWh")
        plt.plot(df_aux["E_kWh"], df_aux["total_cost_eur"], marker="o", label=strategy)

    plt.xlabel("Battery capacity (kWh)")
    plt.ylabel("Total cost (€)")
    plt.title("Battery capacity sensitivity - total cost")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def plot_sensitivity_peak(
    df_sens: pd.DataFrame,
    output_path: str | Path,
) -> None:
    output_path = Path(output_path)

    plt.figure(figsize=(8, 5))
    for strategy in sorted(df_sens["strategy"].unique()):
        df_aux = df_sens[df_sens["strategy"] == strategy].sort_values("E_kWh")
        plt.plot(df_aux["E_kWh"], df_aux["grid_power_peak_kw"], marker="o", label=strategy)

    plt.xlabel("Battery capacity (kWh)")
    plt.ylabel("Peak grid power (kW)")
    plt.title("Battery capacity sensitivity - peak grid power")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def plot_sensitivity_autocons(
    df_sens: pd.DataFrame,
    output_path: str | Path,
) -> None:
    output_path = Path(output_path)

    plt.figure(figsize=(8, 5))
    for strategy in sorted(df_sens["strategy"].unique()):
        df_aux = df_sens[df_sens["strategy"] == strategy].sort_values("E_kWh")
        plt.plot(df_aux["E_kWh"], df_aux["autocons_pct"], marker="o", label=strategy)

    plt.xlabel("Battery capacity (kWh)")
    plt.ylabel("PV self-consumption (%)")
    plt.title("Battery capacity sensitivity - PV self-consumption")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()

def plot_dispatch_detail(
    df_input: pd.DataFrame,
    df_result: pd.DataFrame,
    title: str,
    output_path: str | Path,
) -> None:
    """
    Detailed dispatch plot:
    load, PV, grid import, battery charge and battery discharge.
    """
    output_path = Path(output_path)

    plt.figure(figsize=(12, 6))
    plt.plot(df_input["timestamp"], df_input["load_kw"], label="Load (kW)")
    plt.plot(df_input["timestamp"], df_input["pv_kw"], label="PV available (kW)")
    plt.plot(df_result["timestamp"], df_result["Pg"], label="Grid import (kW)")
    plt.plot(df_result["timestamp"], df_result["Pc"], label="Battery charge (kW)")
    plt.plot(df_result["timestamp"], df_result["Pd"], label="Battery discharge (kW)")

    plt.xlabel("Time")
    plt.ylabel("Power (kW)")
    plt.title(title)
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()