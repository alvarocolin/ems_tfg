from __future__ import annotations

from pathlib import Path
from analysis import run_analysis


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]

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
        "c_deg": 0.04,
    }

    run_analysis(project_root=project_root, params=params)


if __name__ == "__main__":
    main()