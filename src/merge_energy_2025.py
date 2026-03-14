from pathlib import Path
import pandas as pd

INSTALLED_KWP = 1200.0

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

load_path = DATA_DIR / "load_year_2025.csv"
pv_path = DATA_DIR / "madrid_pv_2025_15min_1kwp.csv"
omie_path = DATA_DIR / "omie_2025_uniform_15min.csv"

output_pv_path = DATA_DIR / "pv_2025_1200kwp.csv"
output_merged_path = DATA_DIR / "energy_dataset_2025_15min.csv"

load_df = pd.read_csv(load_path)
pv_df = pd.read_csv(pv_path)
omie_df = pd.read_csv(omie_path)

load_df["timestamp"] = pd.to_datetime(load_df["timestamp"])
pv_df["timestamp"] = pd.to_datetime(pv_df["timestamp"])
omie_df["timestamp_start"] = pd.to_datetime(omie_df["timestamp_start"])

# Escalar FV de 1 kWp a 1200 kWp
pv_1200 = pv_df.copy()
pv_1200["pv_kw"] = pd.to_numeric(pv_1200["pv_power_kw"], errors="coerce") * INSTALLED_KWP
pv_1200["pv_energy_kwh_15min"] = pd.to_numeric(
    pv_1200["pv_energy_kwh_15min"], errors="coerce"
) * INSTALLED_KWP
pv_1200 = pv_1200[["timestamp", "pv_kw", "pv_energy_kwh_15min"]].sort_values("timestamp")

# Limpiar OMIE: priorizar dato real a 15 min
omie_clean = (
    omie_df.sort_values(
        ["timestamp_start", "is_real_15min_market_data"],
        ascending=[True, False]
    )
    .drop_duplicates(subset=["timestamp_start"], keep="first")
    .rename(columns={
        "timestamp_start": "timestamp",
        "price_es_eur_kwh": "price_eur_per_kwh"
    })
)

omie_clean = omie_clean[["timestamp", "price_eur_per_kwh"]].copy()

# Construir malla completa de 15 min para 2025
full_grid = pd.DataFrame({
    "timestamp": pd.date_range(
        "2025-01-01 00:00:00",
        "2025-12-31 23:45:00",
        freq="15min"
    )
})

omie_aligned = full_grid.merge(omie_clean, on="timestamp", how="left").sort_values("timestamp")
omie_aligned = omie_aligned.set_index("timestamp")
omie_aligned["price_eur_per_kwh"] = omie_aligned["price_eur_per_kwh"].interpolate(
    method="time",
    limit_direction="both"
)
omie_aligned = omie_aligned.reset_index()

# Dataset final
merged = (
    load_df[["timestamp", "load_kw"]]
    .merge(pv_1200[["timestamp", "pv_kw"]], on="timestamp", how="inner")
    .merge(omie_aligned[["timestamp", "price_eur_per_kwh"]], on="timestamp", how="inner")
    .sort_values("timestamp")
)

pv_1200.to_csv(output_pv_path, index=False)
merged.to_csv(output_merged_path, index=False)

print("Proceso completado")
print("Producción FV total (kWh):", round(pv_1200["pv_energy_kwh_15min"].sum(), 2))
print("Filas dataset final:", len(merged))
print("Guardado FV en:", output_pv_path)
print("Guardado dataset final en:", output_merged_path)