from __future__ import annotations

from pathlib import Path
from sensitivity import run_battery_sensitivity


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]

    base_params = {
        "E_kWh": 1000.0,
        "Pc_max": 500.0,
        "Pd_max": 500.0,
        "eta_c": 0.95,
        "eta_d": 0.95,
        "soc_min": 0.10,
        "soc_max": 0.90,
        "soc_res": 0.20,
        "soc_init": 0.20,
        "c_deg": 0.04,
    }

    e_values_kwh = [500.0, 1000.0, 1500.0]

    run_battery_sensitivity(
        project_root=project_root,
        base_params=base_params,
        e_values_kwh=e_values_kwh,
    )


if __name__ == "__main__":
    main()