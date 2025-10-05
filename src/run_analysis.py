import pandas as pd
import numpy as np
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data" / "processed" / "water_long.parquet"
OUT = Path(__file__).resolve().parents[1] / "reports"
OUT.mkdir(parents=True, exist_ok=True)

def pct_change_2022_vs_baseline(pvt):
    years = [c for c in pvt.columns if isinstance(c, (int, np.integer))]
    if 2022 not in years:
        return pd.DataFrame(columns=["business_type", "pct_change_vs_baseline"])
    others = [y for y in years if y != 2022]
    baseline = pvt[others].mean(axis=1).replace(0, np.nan)
    delta = (pvt[2022] - baseline) / baseline * 100
    return delta.to_frame("pct_change_vs_baseline").reset_index()

def main():
    df = pd.read_parquet(DATA)
    df["consumption"] = pd.to_numeric(df["consumption"], errors="coerce")

    by_year = df.groupby("year")["consumption"].sum().reset_index()
    by_business = df.groupby(["business_type", "year"], dropna=False)["consumption"].sum().reset_index()
    by_zone = df.groupby(["resource zone", "year"], dropna=False)["consumption"].sum().reset_index()
    by_occ = df.groupby(["occupancy_status", "year"], dropna=False)["consumption"].sum().reset_index() \
        if "occupancy_status" in df.columns else None

    # Save CSVs
    by_year.to_csv(OUT / "total_by_year.csv", index=False)
    by_business.to_csv(OUT / "business_by_year.csv", index=False)
    by_zone.to_csv(OUT / "zone_by_year.csv", index=False)
    if by_occ is not None:
        by_occ.to_csv(OUT / "occupancy_by_year.csv", index=False)

    # 2022 anomalies
    pvt = by_business.pivot(index="business_type", columns="year", values="consumption").fillna(0)
    anomalies = pct_change_2022_vs_baseline(pvt)
    anomalies.to_csv(OUT / "anomalies_2022_vs_baseline.csv", index=False)

    # Write markdown summary
    latest = int(by_year["year"].max())
    summary = [f"# Water Consumption Summary ({by_year['year'].min()}–{latest})"]
    summary.append(f"**Total in {latest}:** {by_year.loc[by_year['year']==latest, 'consumption'].values[0]:,.0f}")

    summary.append("\n## Top Business Types")
    top = by_business[by_business["year"] == latest].sort_values("consumption", ascending=False).head(5)
    for _, r in top.iterrows():
        summary.append(f"- {r['business_type']}: {r['consumption']:,.0f}")

    summary.append("\n## 2022 Anomalies")
    for _, r in anomalies.head(5).iterrows():
        summary.append(f"- {r['business_type']}: {r['pct_change_vs_baseline']:.1f}% change")

    (OUT / "insights.md").write_text("\n".join(summary))
    print("✅ Analysis complete. Check reports/ folder.")

if __name__ == "__main__":
    main()