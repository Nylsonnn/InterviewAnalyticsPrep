import re
import pandas as pd
from pathlib import Path

RAW_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "DRA_exercise.xlsx"
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

COLUMN_ALIASES = {
    "resource zone": ["resource zone", "zone", "rz"],
    "business_type": ["type of business", "account type"],
    "occupancy_status": ["occupancy status", "occupied/vacant", "status"],
    "property_id": ["spid", "id", "site id"],
}

def normalize_columns(df):
    df.columns = [c.strip().lower() for c in df.columns]
    rename = {}
    for target, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in df.columns:
                rename[alias] = target
                break
    df = df.rename(columns=rename)
    return df

def detect_year_columns(df):
    return [c for c in df.columns if re.search(r"20\d{2}", c)]

def main():
    df = pd.read_excel(RAW_PATH)
    df = normalize_columns(df)
    year_cols = detect_year_columns(df)
    id_vars = [c for c in df.columns if c not in year_cols]

    long_df = df.melt(id_vars=id_vars, value_vars=year_cols,
                      var_name="year_col", value_name="consumption")
    long_df["year"] = long_df["year_col"].str.extract(r"(20\d{2})").astype(int)
    long_df["consumption"] = pd.to_numeric(long_df["consumption"], errors="coerce")
    long_df = long_df.dropna(subset=["consumption"])

    long_df.to_parquet(OUT_DIR / "water_long.parquet", index=False)
    long_df.to_csv(OUT_DIR / "water_long.csv", index=False)
    print("✅ Data prepared and saved to data/processed/")

if __name__ == "__main__":
    main()
