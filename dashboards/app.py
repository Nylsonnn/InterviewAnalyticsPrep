import pandas as pd
import numpy as np
from pathlib import Path
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Water Consumption Analytics", layout="wide")

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
PARQUET = DATA_DIR / "water_long.parquet"
CSV_FALLBACK = DATA_DIR / "water_long.csv"

st.title("💧 Water Consumption Analytics (2020–2023)")

# ---------- Load data ----------
@st.cache_data
def load_data():
    if PARQUET.exists():
        df = pd.read_parquet(PARQUET)
    elif CSV_FALLBACK.exists():
        df = pd.read_csv(CSV_FALLBACK)
    else:
        return None
    # clean
    for c in ["business_type", "resource zone", "occupancy_status"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    df["year"] = df["year"].astype(int)
    df["consumption"] = pd.to_numeric(df["consumption"], errors="coerce")
    df = df.dropna(subset=["consumption"])
    return df

df = load_data()
if df is None or df.empty:
    st.warning("No processed data found. Run `python src/prepare_data.py` first.")
    st.stop()

# ---------- Sidebar filters (dropdowns + 'Select all') ----------
st.sidebar.header("Filters")

years_all = sorted(df["year"].unique())
zones_all = sorted(df["resource zone"].unique()) if "resource zone" in df.columns else []
biz_all = sorted(df["business_type"].unique()) if "business_type" in df.columns else []

with st.sidebar.expander("Years", expanded=True):
    years_all_ck = st.checkbox("Select all years", value=True, key="all_years")
    year_sel = years_all[:] if years_all_ck else st.multiselect("Choose years", years_all, default=years_all)

with st.sidebar.expander("Resource Zones", expanded=True):
    if zones_all:
        zones_all_ck = st.checkbox("Select all zones", value=True, key="all_zones")
        zone_sel = zones_all[:] if zones_all_ck else st.multiselect("Choose zones", zones_all, default=zones_all)
    else:
        zone_sel = []

with st.sidebar.expander("Business Types", expanded=True):
    if biz_all:
        biz_all_ck = st.checkbox("Select all business types", value=True, key="all_biz")
        default_biz = biz_all if len(biz_all) <= 15 else biz_all[:15]
        biz_sel = biz_all[:] if biz_all_ck else st.multiselect("Choose business types", biz_all, default=default_biz)
    else:
        biz_sel = []

if st.sidebar.button("Reset filters"):
    st.session_state.clear()
    st.experimental_rerun()

# ---------- Apply filters + friendly guard ----------
dff = df[df["year"].isin(year_sel)]
if zones_all:
    dff = dff[dff["resource zone"].isin(zone_sel)]
if biz_all and biz_sel:
    dff = dff[dff["business_type"].isin(biz_sel)]

if len(year_sel) == 0 or dff.empty:
    st.warning("No data selected. Adjust filters on the left.")
    st.stop()

# ---------- KPIs ----------
def kpi(col, label, value, help_text=None):
    col.metric(label, f"{value:,.0f}", help=help_text)

total = dff["consumption"].sum()
yr2022_total = dff.loc[dff["year"] == 2022, "consumption"].sum() if 2022 in dff["year"].unique() else 0
vacant_total = 0
if "occupancy_status" in dff.columns:
    vacant_total = dff.loc[dff["occupancy_status"].str.contains("vacant", case=False, na=False), "consumption"].sum()

c1, c2, c3, c4 = st.columns(4)
kpi(c1, "Total (current filters)", total)
kpi(c2, "Total in 2022", yr2022_total, "Hot/dry benchmark")
if "occupancy_status" in dff.columns:
    kpi(c3, "Vacant consumption", vacant_total)
kpi(c4, "Rows in view", len(dff))

st.divider()

# ---------- Tabs ----------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1) Business Type (YoY Top)", "2) Vacant Trend", "3) 2022 Anomalies", "4) Resource Zones", "Data Explorer"
])

# ==== 1) What type of business year-on-year is using the most water? ====
with tab1:
    st.subheader("Year-on-Year: Top Business Type")
    if "business_type" in dff.columns:
        byb = (
            dff.groupby(["business_type", "year"], dropna=False)["consumption"]
            .sum()
            .reset_index()
        )
        # For each year, pick the business with the highest consumption
        top_by_year = byb.sort_values(["year", "consumption"], ascending=[True, False]).groupby("year").head(1)
        # Narrative answer
        bullets = "\n".join([f"- **{int(y)}:** {bt} ({cons:,.0f})"
                             for y, bt, cons in zip(top_by_year["year"], top_by_year["business_type"], top_by_year["consumption"])])
        st.markdown(f"Highest-consuming business type by year is:\n\n{bullets}")

        # Chart
        fig = px.bar(byb, x="year", y="consumption", color="business_type",
                     title="Yearly Consumption by Business Type", barmode="stack")
        st.plotly_chart(fig, use_container_width=True)

        # Download evidence
        st.download_button("Download top-by-year (CSV)",
                           data=top_by_year.to_csv(index=False).encode("utf-8"),
                           file_name="top_business_type_by_year.csv",
                           mime="text/csv")
    else:
        st.info("No `business_type` column detected.")

# ==== 2) How much water is consumed by 'vacant' and is it increasing or decreasing? ====
with tab2:
    st.subheader("Vacant Properties – Total & Trend")
    if "occupancy_status" in dff.columns:
        occ = dff.groupby(["occupancy_status", "year"])["consumption"].sum().reset_index()
        vac = occ[occ["occupancy_status"].str.contains("vacant", case=False, na=False)].copy()
        if not vac.empty:
            # Trend direction: slope sign from linear fit (year vs consumption)
            years_num = vac["year"].astype(int)
            slope = np.polyfit(years_num, vac["consumption"], 1)[0] if len(vac) >= 2 else 0
            direction = "increasing" if slope > 0 else ("decreasing" if slope < 0 else "flat")

            total_line = px.line(vac, x="year", y="consumption", markers=True, title="Vacant Consumption by Year")
            st.plotly_chart(total_line, use_container_width=True)

            # Share of total
            total_by_year = dff.groupby("year")["consumption"].sum().rename("total").reset_index()
            share = vac.merge(total_by_year, on="year")
            share["vacant_share_%"] = 100 * share["consumption"] / share["total"]

            # Narrative answer
            first_y, last_y = share["year"].min(), share["year"].max()
            first_v, last_v = share.loc[share["year"] == first_y, "consumption"].item(), share.loc[share["year"] == last_y, "consumption"].item()
            st.markdown(
                f"**Answer:** Vacant properties used **{last_v:,.0f}** in **{int(last_y)}** "
                f"(was {first_v:,.0f} in {int(first_y)}), so the trend is **{direction}**."
            )
            st.dataframe(share.sort_values("year"))

            st.download_button("Download vacant trend (CSV)",
                               data=share.to_csv(index=False).encode("utf-8"),
                               file_name="vacant_share_by_year.csv",
                               mime="text/csv")
        else:
            st.info("No rows identified as vacant in the filtered data.")
    else:
        st.info("No `occupancy_status` column detected.")

# ==== 3) 2022 hot/dry year: industries with significantly higher usage than other years ====
with tab3:
    st.subheader("2022 Anomalies vs Baseline (Other Years)")
    if "business_type" in df.columns and 2022 in df["year"].unique():
        base = df.groupby(["business_type", "year"])["consumption"].sum().reset_index()
        pvt = base.pivot(index="business_type", columns="year", values="consumption").fillna(0)
        other_years = [y for y in pvt.columns if y != 2022]
        if other_years:
            pvt["baseline"] = pvt[other_years].mean(axis=1).replace(0, np.nan)
            pvt["pct_change_2022_vs_baseline"] = (pvt[2022] - pvt["baseline"]) / pvt["baseline"] * 100
            # significance filter: >= +20% and 2022 volume above the median to avoid tiny bases
            median_2022 = pvt[2022].median()
            sig = pvt[(pvt["pct_change_2022_vs_baseline"] >= 20) & (pvt[2022] >= median_2022)].sort_values("pct_change_2022_vs_baseline", ascending=False).reset_index()
            # Narrative answer
            if sig.empty:
                st.markdown("**Answer:** No business types show a materially higher 2022 usage (≥20% above baseline and above-median volume).")
            else:
                bullets = "\n".join([f"- **{bt}**: {chg:.1f}% above baseline (2022 volume {vol:,.0f})"
                                     for bt, chg, vol in zip(sig["business_type"], sig["pct_change_2022_vs_baseline"], sig[2022])])
                st.markdown("**Answer — Significant increases in 2022:**\n" + bullets)

            # Show top increases/decreases for transparency
            out = pvt.sort_values("pct_change_2022_vs_baseline", ascending=False).reset_index()
            c1, c2 = st.columns(2)
            with c1:
                top_pos = out.head(10)
                figp = px.bar(top_pos, x="business_type", y="pct_change_2022_vs_baseline",
                              title="Largest Increases in 2022 (vs baseline avg)")
                st.plotly_chart(figp, use_container_width=True)
            with c2:
                top_neg = out.tail(10).sort_values("pct_change_2022_vs_baseline")
                fign = px.bar(top_neg, x="business_type", y="pct_change_2022_vs_baseline",
                              title="Largest Decreases in 2022 (vs baseline avg)")
                st.plotly_chart(fign, use_container_width=True)

            st.download_button("Download anomaly table (CSV)",
                               data=out[["business_type", "pct_change_2022_vs_baseline"]].to_csv(index=False).encode("utf-8"),
                               file_name="anomalies_2022_vs_baseline.csv",
                               mime="text/csv")
        else:
            st.info("Need at least one non-2022 year to form a baseline.")
    else:
        st.info("No 2022 in the dataset or `business_type` is missing.")

# ==== 4) Which resource zone is using the most water? ====
with tab4:
    st.subheader("Resource Zones – Highest Usage")
    if "resource zone" in dff.columns:
        byz = dff.groupby(["resource zone", "year"])["consumption"].sum().reset_index()
        fig = px.area(byz, x="year", y="consumption", color="resource zone",
                      title="Yearly Consumption by Resource Zone")
        st.plotly_chart(fig, use_container_width=True)

        latest = max(year_sel) if len(year_sel) else int(df["year"].max())
        latest_rank = byz[byz["year"] == latest].sort_values("consumption", ascending=False)

        # Narrative answer
        if not latest_rank.empty:
            top_zone = latest_rank.iloc[0]
            st.markdown(f"**Answer:** In **{latest}**, the highest-consuming resource zone is **{top_zone['resource zone']}** "
                        f"with **{top_zone['consumption']:,.0f}**.")
        st.dataframe(latest_rank.reset_index(drop=True))

        st.download_button("Download zone table (CSV)",
                           data=byz.to_csv(index=False).encode("utf-8"),
                           file_name="zone_by_year.csv",
                           mime="text/csv")
    else:
        st.info("No `resource zone` column detected.")

# ---- Data Explorer ----
with tab5:
    st.subheader("Data Explorer")
    st.dataframe(dff.sort_values(["year"], ascending=True))
    st.download_button(
        "Download filtered dataset (CSV)",
        data=dff.to_csv(index=False).encode("utf-8"),
        file_name="filtered_data.csv",
        mime="text/csv"
    )
