from __future__ import annotations

from pathlib import Path

from data_loader import load_input_data, infer_timestep_hours
from baselines import run_s0, run_s1
from kpis import compute_kpis


def main() -> None:
    # Paths
    project_root = Path(__file__).resolve().parents[1]
    input_path = project_root / "data" / "input_day.csv"

    output_s0 = project_root / "results" / "s0_results.csv"
    output_s1 = project_root / "results" / "s1_results.csv"

    # Load data
    df_input = load_input_data(input_path)
    dt_h = infer_timestep_hours(df_input)

    # Battery/system parameters
    params = {
        "E_kWh": 1000.0,
        "Pc_max": 500.0,
        "Pd_max": 500.0,
        "eta_c": 0.95,
        "eta_d": 0.95,
        "soc_min": 0.10,
        "soc_max": 0.90,
        "soc_res": 0.20,
        "soc_init": 0.20,
    }

    print("✅ Datos cargados correctamente")
    print(f"Número de filas: {len(df_input)}")
    print(f"Paso temporal: {dt_h:.4f} h")

    # --- S0 ---
    df_s0 = run_s0(df_input)
    kpis_s0 = compute_kpis(df_input=df_input, df_result=df_s0, dt_h=dt_h, e_kwh=params["E_kWh"])
    df_s0.to_csv(output_s0, index=False)

    # --- S1 ---
    df_s1 = run_s1(df_input=df_input, params=params, dt_h=dt_h)
    kpis_s1 = compute_kpis(df_input=df_input, df_result=df_s1, dt_h=dt_h, e_kwh=params["E_kWh"])
    df_s1.to_csv(output_s1, index=False)

    print("\n✅ Estrategias ejecutadas correctamente")

    print("\n--- S0: Sin batería ---")
    print(f"Coste total (€): {kpis_s0['cost_eur']:.2f}")
    print(f"Autoconsumo FV (%): {kpis_s0['autocons_pct']:.2f}")
    print(f"Energía descargada batería (kWh): {kpis_s0['discharged_energy_kwh']:.2f}")
    print(f"Ciclos equivalentes: {kpis_s0['cycles_eq']:.4f}")

    print("\n--- S1: Autoconsumo máximo con batería ---")
    print(f"Coste total (€): {kpis_s1['cost_eur']:.2f}")
    print(f"Autoconsumo FV (%): {kpis_s1['autocons_pct']:.2f}")
    print(f"Energía descargada batería (kWh): {kpis_s1['discharged_energy_kwh']:.2f}")
    print(f"Ciclos equivalentes: {kpis_s1['cycles_eq']:.4f}")

    print(f"\nResultados guardados en:\n- {output_s0}\n- {output_s1}")


if __name__ == "__main__":
    main()