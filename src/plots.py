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