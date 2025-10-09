# dashboards/app.py
import pandas as pd
import numpy as np
from pathlib import Path
import streamlit as st
import plotly.express as px
from PIL import Image

# ---------- SE Water Theming ----------
SE_TEAL = "#00A9B7"
SE_NAVY = "#00263A"
SE_BG = "#F5F7FA"
SE_WHITE = "#FFFFFF"
SE_LightBlue = "#22E5F7"

st.set_page_config(page_title="Water Consumption Analytics | SE Water", layout="wide", page_icon="💧")

# ---- Colour helpers (distinct + colour-blind friendly) ----
import plotly.express as px

# Okabe–Ito (colour-blind safe) + some extras for larger category sets
OKABE_ITO = [
    "#86D36F", "#E69F00", "#56B4E9", "#009E73",
    "#F0E442", "#0072B2", "#D55E00", "#CC79A7", "#999999"
]
EXTRA = px.colors.qualitative.Set3 + px.colors.qualitative.D3 + px.colors.qualitative.Bold
MASTER_PALETTE = OKABE_ITO + EXTRA  # big, high-contrast palette

def build_color_map(values, palette=MASTER_PALETTE):
    """Return a stable dict {value: color} covering all category values."""
    uniq = list(dict.fromkeys(values))                 # preserve order, de-dupe
    need = len(uniq)
    base = (palette * ((need // len(palette)) + 1))[:need]
    return {k: c for k, c in zip(uniq, base)}

def category_args(df, col, order=None):
    """Convenience: consistent order + colours for a column."""
    order = order or list(dict.fromkeys(df[col].dropna()))
    cmap = build_color_map(order)
    return dict(category_orders={col: order}, color_discrete_map=cmap)


import plotly.io as pio

pio.templates["sewater"] = pio.templates["plotly_white"]
pio.templates["sewater"].layout.update(
    font=dict(color=SE_NAVY, family="Arial"),
    paper_bgcolor=SE_WHITE,
    plot_bgcolor=SE_WHITE,
    title_font=dict(color=SE_NAVY, size=18),
    xaxis=dict(showgrid=True, gridcolor="#DDDDDD", zeroline=False),
    yaxis=dict(showgrid=True, gridcolor="#DDDDDD", zeroline=False),
)
pio.templates.default = "sewater"


st.markdown(
    f"""
    <style>
    /* -------- Sidebar: keep it light with readable text -------- */
    section[data-testid="stSidebar"] {{
        background:#FFFFFF !important;
        color:{SE_NAVY} !important;
        border-right:1px solid #e0e0e0;
    }}

    /* Expander header row: 'Years', 'Resource Zones', 'Business Types' */
    section[data-testid="stSidebar"] div[data-testid="stExpander"] > details > summary {{
        background:#FFFFFF !important;
        color:{SE_NAVY} !important;
        border:1px solid #D0D7DE !important;
        border-radius:8px !important;
        padding:6px 10px;
    }}
    /* Chevron icon colour */
    section[data-testid="stSidebar"] div[data-testid="stExpander"] > details > summary svg {{
        fill:{SE_NAVY} !important;
    }}

    /* Expander content area */
    section[data-testid="stSidebar"] div[data-testid="stExpander"] > details > div[role="region"] {{
        background:#FFFFFF !important;
        color:{SE_NAVY} !important;
        border:1px solid #D0D7DE !important;
        border-top:none !important;
        border-radius:0 0 8px 8px !important;
        padding:8px 10px;
    }}

    /* Make ALL labels/text inside the filters readable */
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] p {{
        color:{SE_NAVY} !important;
    }}
    /* Checkbox label text specifically */
    section[data-testid="stSidebar"] input[type="checkbox"] + div p {{
        color:{SE_NAVY} !important;
    }}

    /* Reset button look */
    section[data-testid="stSidebar"] button[kind="secondary"] {{
        background:{SE_TEAL} !important;
        color:#FFFFFF !important;
        border:none !important;
        border-radius:8px !important;
    }}
    section[data-testid="stSidebar"] button[kind="secondary"]:hover {{
        background:{SE_LightBlue} !important;
        color:#FFFFFF !important;
    }}

    /* -------- Tabs: -------- */
    .stTabs [role="tablist"] {{
        background:{SE_NAVY};
        border-radius:6px;
        padding:4px;
    }}
    .stTabs [role="tab"] {{ color:#FFFFFF !important; }}
    .stTabs [aria-selected="true"] {{
        border-bottom:3px solid {SE_TEAL} !important;
        color:{SE_TEAL} !important;
        font-weight:700;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)




# ---------- Header with logo ----------
from PIL import Image
LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "se_water_logo.png"

# Sidebar logo (centered)
if LOGO_PATH.exists():
    with st.sidebar:
        st.markdown(
            "<div style='text-align:center; padding:6px 0 12px 0;'>",
            unsafe_allow_html=True,
        )
        st.image(str(LOGO_PATH), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# Header title (no logo here so it stays readable on dark bg)
st.markdown(
    "<h1 style='margin-top:0'>Water Consumption Analytics (2020–2024)</h1>",
    unsafe_allow_html=True,
)
st.caption(
    "Answers: top business type (YoY), vacant trend, 2022 anomalies, and highest-use resource zones."
)

# ---------- Load data ----------
DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
PARQUET = DATA_DIR / "water_long.parquet"
CSV_FALLBACK = DATA_DIR / "water_long.csv"

@st.cache_data
def load_data():
    if PARQUET.exists():
        df = pd.read_parquet(PARQUET)
    elif CSV_FALLBACK.exists():
        df = pd.read_csv(CSV_FALLBACK)
    else:
        return None
    for c in ["business_type", "resource zone", "occupancy_status"]:
        if c in df.columns: df[c] = df[c].astype(str).str.strip()
    df["year"] = df["year"].astype(int)
    df["consumption"] = pd.to_numeric(df["consumption"], errors="coerce")
    return df.dropna(subset=["consumption"])

df = load_data()
if df is None or df.empty:
    st.warning("No processed data found. Run `python src/prepare_data.py` first.")
    st.stop()

# ---------- Sidebar filters (dropdowns with 'Select all') ----------
st.sidebar.header("Filters")

years_all = sorted(df["year"].unique())
zones_all = sorted(df["resource zone"].unique()) if "resource zone" in df.columns else []
biz_all   = sorted(df["business_type"].unique()) if "business_type" in df.columns else []

with st.sidebar.expander("Years", expanded=True):
    ck_all_years = st.checkbox("Select all years", value=True, key="all_years")
    year_sel = years_all[:] if ck_all_years else st.multiselect("Choose years", years_all, default=years_all)

with st.sidebar.expander("Resource Zones", expanded=True):
    if zones_all:
        ck_all_zones = st.checkbox("Select all zones", value=True, key="all_zones")
        zone_sel = zones_all[:] if ck_all_zones else st.multiselect("Choose zones", zones_all, default=zones_all)
    else:
        zone_sel = []

with st.sidebar.expander("Business Types", expanded=True):
    if biz_all:
        ck_all_biz = st.checkbox("Select all business types", value=True, key="all_biz")
        default_biz = biz_all if len(biz_all) <= 15 else biz_all[:15]
        biz_sel = biz_all[:] if ck_all_biz else st.multiselect("Choose business types", biz_all, default=default_biz)
    else:
        biz_sel = []

if st.sidebar.button("Reset filters"):
    st.session_state.clear()
    st.experimental_rerun()

# ---------- Apply filters + friendly guard ----------
dff = df[df["year"].isin(year_sel)]
if zones_all: dff = dff[dff["resource zone"].isin(zone_sel)]
if biz_all and biz_sel: dff = dff[dff["business_type"].isin(biz_sel)]

if len(year_sel) == 0 or dff.empty:
    st.warning("No data selected. Adjust filters on the left.")
    st.stop()

# ---------- KPIs ----------
def kpi(col, label, value, help_text=None):
    col.metric(label, f"{value:,.0f}", help=help_text)

total = dff["consumption"].sum()
yr2022 = dff.loc[dff["year"]==2022, "consumption"].sum() if 2022 in dff["year"].unique() else 0
vacant = 0
if "occupancy_status" in dff.columns:
    vacant = dff.loc[dff["occupancy_status"].str.contains("vacant", case=False, na=False),"consumption"].sum()

c1, c2, c3, c4 = st.columns(4)
kpi(c1, "Total (filters)", total)
kpi(c2, "Total in 2022", yr2022, "Hot/dry benchmark")
if "occupancy_status" in dff.columns: kpi(c3, "Vacant consumption", vacant)
kpi(c4, "Rows in view", len(dff))

st.divider()

# ---------- Tabs ----------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Business Type", "Vacant Trend", "2022 Anomalies", "Resource Zones", "Data Explorer"
])

# ---- Business Types ----
with tab1:
    st.subheader("Year-on-Year Water Use by Business Type")
    if "business_type" in df.columns:
        byb = df.groupby(["business_type", "year"], dropna=False)["consumption"].sum().reset_index()

        args = category_args(byb, "business_type")  # 🔹 this builds consistent colours

        fig = px.bar(
            byb, x="year", y="consumption", color="business_type",
            title="Consumption by Business Type (Yearly)", barmode="stack",
            **args  # 🔹 pass in consistent colour + order
        )
        st.plotly_chart(fig, use_container_width=True)

        latest = max(year_sel) if len(year_sel) else int(df["year"].max())
        top_latest = byb[byb["year"] == latest].sort_values("consumption", ascending=False)

        fig2 = px.bar(
            top_latest.head(15), x="business_type", y="consumption",
            title=f"Top Business Types in {latest}", text_auto=True,
            **args  # 🔹 use same colours here too
        )
        fig2.update_layout(xaxis_title=None)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No `business_type` column detected.")


# ---- Vacant Trend ----
with tab2:
    st.subheader("Vacant Property Consumption")
    if "occupancy_status" in df.columns:
        occ = df.groupby(["occupancy_status", "year"])["consumption"].sum().reset_index()
        vac = occ[occ["occupancy_status"].str.contains("vacant", case=False, na=False)]
        if not vac.empty:
            vac["year"] = vac["year"].astype(str)
            fig = px.line(
                vac, x="year", y="consumption", markers=True,
                title="Vacant Consumption by Year",
                color_discrete_sequence=MASTER_PALETTE
            )
            st.plotly_chart(fig, use_container_width=True)

            total_by_year = df.groupby("year")["consumption"].sum().rename("total").reset_index()
            total_by_year["year"] = total_by_year["year"].astype(str)
            share = vac.merge(total_by_year, on="year")
            share["vacant_share_%"] = 100 * share["consumption"] / share["total"]
            st.dataframe(share.sort_values("year"))
        else:
            st.info("No rows identified as vacant in the filtered data.")
    else:
        st.info("No `occupancy_status` column detected.")




# ---- 2022 Anomalies ----
with tab3:
    st.subheader("2022 Anomalies vs Baseline")
    if "business_type" in df.columns and 2022 in df["year"].unique():
        base = df.groupby(["business_type", "year"])["consumption"].sum().reset_index()
        pvt = base.pivot(index="business_type", columns="year", values="consumption").fillna(0)
        others = [y for y in pvt.columns if y != 2022]
        if others:
            pvt["baseline"] = pvt[others].mean(axis=1).replace(0, np.nan)
            pvt["pct_change_2022_vs_baseline"] = (pvt[2022] - pvt["baseline"]) / pvt["baseline"] * 100
            out = pvt.sort_values("pct_change_2022_vs_baseline", ascending=False).reset_index()

            figp = px.bar(
                out.head(10),
                x="business_type",
                y="pct_change_2022_vs_baseline",
                title="Largest Increases in 2022 (vs baseline)",
                color_discrete_sequence=MASTER_PALETTE,
                labels={
                    "business_type": "Business Type",
                    "pct_change_2022_vs_baseline": "% Change from Baseline (2022)"
                }
            )
            st.plotly_chart(figp, use_container_width=True, key="anoms_main_bar")
        else:
            st.info("Need at least one non-2022 year to form a baseline.")
    else:
        st.info("No 2022 in data or `business_type` missing.")


# ---- Resource Zones ----
with tab4:
    st.subheader("Usage by Resource Zone")
    if "resource zone" in df.columns:
        byz = df.groupby(["resource zone", "year"])["consumption"].sum().reset_index()
        byz["year"] = byz["year"].astype(str)

        fig = px.area(
            byz, x="year", y="consumption", color="resource zone",
            title="Yearly Consumption by Resource Zone",
            color_discrete_sequence=MASTER_PALETTE
        )
        st.plotly_chart(fig, use_container_width=True, key="rz_area")

        latest = max(year_sel) if len(year_sel) else int(df["year"].max())
        latest_rank = byz[byz["year"] == str(latest)].sort_values("consumption", ascending=False)

        fig2 = px.bar(
            latest_rank, x="resource zone", y="consumption",
            title=f"Resource Zones Ranked ({latest})",
            text_auto=True,
            color_discrete_sequence=MASTER_PALETTE
        )
        fig2.update_layout(xaxis_title=None)
        st.plotly_chart(fig2, use_container_width=True, key="rz_rank")
    else:
        st.info("No `resource zone` column detected.")

        

# ---- Data Explorer ----
with tab5:
    st.subheader("Data Explorer")
    st.dataframe(dff.sort_values(["year"], ascending=True))
