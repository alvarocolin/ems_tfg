from __future__ import annotations

import time
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path

import pandas as pd
import requests


BASE_NEW = "https://www.omie.es/en/file-download"
BASE_OLD = "https://www.omie.es/sites/default/files/dados"


def build_new_url(date: datetime, version: int) -> str:
    filename = f"marginalpdbc_{date:%Y%m%d}.{version}"
    return f"{BASE_NEW}?filename={filename}&parents=marginalpdbc"


def build_old_url(date: datetime) -> str:
    date_str = date.strftime("%Y%m%d")
    return (
        f"{BASE_OLD}/AGNO_{date:%Y}/MES_{date:%m}/TXT/"
        f"INT_PBC_EV_H_1_{date_str}_{date_str}.TXT"
    )


def fetch_text(url: str, session: requests.Session, timeout: int = 20) -> str | None:
    try:
        r = session.get(
            url,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "text/plain,text/html,*/*",
            },
        )
        if r.status_code != 200:
            return None

        text = r.text.strip()
        if not text or text == "*":
            return None

        return text
    except requests.RequestException:
        return None


def parse_new_marginalpdbc(text: str) -> pd.DataFrame | None:
    """
    Parse official OMIE file:
    MARGINALPDBC;
    2025;10;01;1;xx;yy;
    ...
    """
    rows = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line == "*" or line.startswith("MARGINALPDBC"):
            continue

        parts = [p.strip() for p in line.split(";") if p.strip() != ""]
        if len(parts) < 6:
            continue

        try:
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
            period = int(parts[3])
            price_pt = float(parts[4].replace(",", "."))
            price_es = float(parts[5].replace(",", "."))
        except ValueError:
            continue

        rows.append(
            {
                "date": datetime(year, month, day).date(),
                "period": period,
                "price_pt_eur_mwh": price_pt,
                "price_es_eur_mwh": price_es,
            }
        )

    if not rows:
        return None

    return pd.DataFrame(rows)


def parse_old_txt(text: str, date: datetime) -> pd.DataFrame | None:
    """
    Parse old TXT format fallback.
    Expected semicolon-separated lines where:
    parts[2] = hour
    parts[5] = price
    """
    rows = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        parts = [p.strip() for p in line.split(";")]
        if len(parts) < 6:
            continue

        try:
            hour = int(parts[2])
            price = float(parts[5].replace(",", "."))
        except ValueError:
            continue

        rows.append(
            {
                "date": date.date(),
                "period": hour,
                "price_pt_eur_mwh": pd.NA,
                "price_es_eur_mwh": price,
            }
        )

    if not rows:
        return None

    return pd.DataFrame(rows)


def period_to_timestamp_15m(date_value, period: int) -> datetime:
    """
    Convert OMIE period to timestamp start.
    - Hourly day: period 1..24 (or 25 on DST day)
    - Quarter-hour day: period 1..96 (or 100 on DST day)
    """
    base = datetime.combine(date_value, datetime.min.time())

    # quarter-hour resolution
    if period > 25:
        return base + timedelta(minutes=(period - 1) * 15)

    # hourly resolution
    return base + timedelta(hours=(period - 1))


def expand_hourly_to_quarter_hour(df: pd.DataFrame) -> pd.DataFrame:
    """
    For hourly rows, replicate each hour into 4 quarter-hours.
    This is NOT real quarter-hour market data; it is repeated hourly price.
    """
    expanded_rows = []

    for _, row in df.iterrows():
        ts = row["timestamp_start"]
        for k in range(4):
            new_row = row.copy()
            new_row["timestamp_start"] = ts + timedelta(minutes=15 * k)
            new_row["source_resolution"] = "hourly_repeated_to_15min"
            new_row["is_real_15min_market_data"] = False
            expanded_rows.append(new_row)

    return pd.DataFrame(expanded_rows)


def download_day(date: datetime, session: requests.Session) -> pd.DataFrame | None:
    """
    Tries:
    1) New official OMIE file marginalpdbc_YYYYMMDD.v
    2) Old TXT fallback
    """
    # First try new official format with versions 1..5
    for version in range(1, 6):
        text = fetch_text(build_new_url(date, version), session)
        if text:
            df = parse_new_marginalpdbc(text)
            if df is not None and not df.empty:
                df["source_file_version"] = version
                df["download_format"] = "marginalpdbc"
                return df

    # Fallback to old TXT
    text_old = fetch_text(build_old_url(date), session)
    if text_old:
        df = parse_old_txt(text_old, date)
        if df is not None and not df.empty:
            df["source_file_version"] = pd.NA
            df["download_format"] = "legacy_txt"
            return df

    return None


def download_year_2025(session: requests.Session) -> tuple[pd.DataFrame, list[str]]:
    start = datetime(2025, 1, 1)
    end = datetime(2025, 12, 31)

    day = start
    dfs: list[pd.DataFrame] = []
    failed_days: list[str] = []

    while day <= end:
        print(f"Downloading {day:%Y-%m-%d} ...")
        df = download_day(day, session)

        if df is None or df.empty:
            failed_days.append(day.strftime("%Y-%m-%d"))
        else:
            dfs.append(df)

        day += timedelta(days=1)
        time.sleep(0.15)

    if not dfs:
        raise RuntimeError(
            "No se ha podido descargar ningún fichero de OMIE. "
            "Revisa conexión, formato, cambios en la web o URLs."
        )

    all_df = pd.concat(dfs, ignore_index=True)

    # Build timestamps
    all_df["timestamp_start"] = all_df.apply(
        lambda r: period_to_timestamp_15m(r["date"], int(r["period"])),
        axis=1,
    )

    # Identify real 15-min market data
    all_df["is_real_15min_market_data"] = all_df["period"] > 25
    all_df["source_resolution"] = all_df["period"].apply(
        lambda p: "quarter_hour" if p > 25 else "hourly"
    )

    return all_df, failed_days


def build_uniform_15m_series(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a uniform 15-min series for all 2025:
    - real 15-min data kept as-is
    - hourly data repeated into 4 quarter-hours
    """
    qh_real = df[df["source_resolution"] == "quarter_hour"].copy()

    hourly = df[df["source_resolution"] == "hourly"].copy()
    hourly_15m = expand_hourly_to_quarter_hour(hourly)

    out = pd.concat([hourly_15m, qh_real], ignore_index=True)
    out = out.sort_values("timestamp_start").reset_index(drop=True)

    out["price_es_eur_kwh"] = pd.to_numeric(out["price_es_eur_mwh"], errors="coerce") / 1000
    out["price_pt_eur_kwh"] = pd.to_numeric(out["price_pt_eur_mwh"], errors="coerce") / 1000

    return out


def main():
    project_root = Path(__file__).resolve().parents[1]
    output_dir = project_root / "data"
    output_dir.mkdir(parents=True, exist_ok=True)

    with requests.Session() as session:
        raw_df, failed_days = download_year_2025(session)

    raw_df = raw_df.sort_values(["date", "period"]).reset_index(drop=True)
    raw_df["price_es_eur_kwh"] = pd.to_numeric(raw_df["price_es_eur_mwh"], errors="coerce") / 1000
    raw_df["price_pt_eur_kwh"] = pd.to_numeric(raw_df["price_pt_eur_mwh"], errors="coerce") / 1000

    uniform_15m_df = build_uniform_15m_series(raw_df)

    raw_path = output_dir / "omie_2025_raw_market_periods.csv"
    qh_path = output_dir / "omie_2025_uniform_15min.csv"
    failed_path = output_dir / "omie_2025_failed_days.txt"

    raw_df.to_csv(raw_path, index=False)
    uniform_15m_df.to_csv(qh_path, index=False)

    failed_path.write_text("\n".join(failed_days), encoding="utf-8")

    print("\nDescarga completada")
    print(f"Filas raw: {len(raw_df):,}")
    print(f"Filas 15 min uniformes: {len(uniform_15m_df):,}")
    print(f"Días fallidos: {len(failed_days)}")
    print(f"Raw guardado en: {raw_path}")
    print(f"15 min guardado en: {qh_path}")
    print(f"Log fallos guardado en: {failed_path}")


if __name__ == "__main__":
    main()