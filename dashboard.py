"""
Offers Performance Dashboard — Streamlit
Run with:  streamlit run dashboard.py
Requires:  pip install streamlit pandas plotly requests
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import date, timedelta
from io import StringIO

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Offers Performance Dashboard",
    page_icon="📊",
    layout="wide",
)

# ─── CUSTOM CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

[data-testid="stAppViewContainer"] { background: #0d0f14; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] {
    background: #161a23;
    border-right: 1px solid #2a3045;
}
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    color: #e8ecf5;
}
[data-testid="metric-container"] {
    background: #161a23;
    border: 1px solid #2a3045;
    border-radius: 12px;
    padding: 16px 20px;
}
[data-testid="metric-container"] label {
    font-size: 0.72rem !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #6b7694 !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family: 'Space Mono', monospace !important;
    font-size: 1.5rem !important;
    font-weight: 700 !important;
}
.section-header {
    font-family: 'Space Mono', monospace;
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #6b7694;
    margin: 24px 0 12px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid #2a3045;
}
.wow-info {
    background: #161a23;
    border: 1px solid #2a3045;
    border-left: 3px solid #4f8ef7;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 0.78rem;
    color: #8a93b2;
    margin-bottom: 12px;
}
hr { border-color: #2a3045 !important; }
</style>
""", unsafe_allow_html=True)


# ─── GOOGLE SHEETS DATA LOADER ────────────────────────────────────────────────
SHEET_ID      = "1P51zcUKZR-MmpIW84BH1HpH07LTUAK3MH6KVCCwFIRA"
SHEET_CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"

EXPECTED_COLUMNS = [
    "Date",
    "Excel Activations",
    "Excel Redemptions",
    "Extraordinaire Activations",
    "Extraordinaire Redemptions",
    "Unique Shoppers",
    "Cashback Amount",
]

@st.cache_data(ttl=300)   # auto-refreshes every 5 minutes; press R to force-refresh
def load_data():
    try:
        response = requests.get(SHEET_CSV_URL, timeout=15)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text))
    except Exception as e:
        st.error(f"❌ Could not load Google Sheet: {e}")
        st.info(
            "**Troubleshooting:**\n"
            "1. Share the sheet as **Anyone with the link → Viewer**.\n"
            "2. Confirm the Sheet ID in the code matches your URL.\n"
            "3. Column names must match exactly: " + ", ".join(f"`{c}`" for c in EXPECTED_COLUMNS)
        )
        st.stop()

    # Validate columns
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        st.error(
            f"❌ Missing columns: **{missing}**\n\n"
            f"Expected: {EXPECTED_COLUMNS}\n\nFound: {list(df.columns)}"
        )
        st.stop()

    df = df[EXPECTED_COLUMNS].copy()

    # Parse date — handles "25 Mar", "25 Mar 2026", "2026-03-25", etc.
    df["Date"] = pd.to_datetime(df["Date"], infer_datetime_format=True, dayfirst=True)

    # Coerce numeric columns (handle commas like "1,048")
    for col in EXPECTED_COLUMNS[1:]:
        df[col] = (
            pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")
            .fillna(0)
        )

    return df.sort_values("Date").reset_index(drop=True)


# ─── LOAD DATA ────────────────────────────────────────────────────────────────
df_all = load_data()

# ─── PLOTLY THEME ─────────────────────────────────────────────────────────────
CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans", color="#8a93b2", size=12),
    xaxis=dict(
        gridcolor="#1e2330", linecolor="#2a3045",
        tickfont=dict(size=11, color="#6b7694"), showgrid=False,
    ),
    yaxis=dict(
        gridcolor="#1e2330", linecolor="#2a3045",
        tickfont=dict(size=11, color="#6b7694"),
    ),
    legend=dict(
        bgcolor="rgba(22,26,35,0.8)", bordercolor="#2a3045", borderwidth=1,
        font=dict(size=11, color="#e8ecf5"),
    ),
    margin=dict(l=10, r=10, t=30, b=10),
    hovermode="x unified",
)

C_EXCEL     = "#4f8ef7"
C_EXTRA     = "#f7714f"
C_CASHBACK  = "#4fd9a0"
C_SHOPPERS  = "#f7d44f"
C_PREV_WEEK = "#a78bfa"   # purple for previous-week overlay


# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📅 Date Filter")
    st.markdown("---")

    filter_choice = st.radio(
        "Select period",
        options=["1 Day", "7 Days", "10 Days", "15 Days", "30 Days", "Custom Range"],
        index=4,   # default: 30 Days
    )

    min_date = df_all["Date"].min().date()
    max_date = df_all["Date"].max().date()

    if filter_choice == "Custom Range":
        start_date = st.date_input("Start date", value=min_date, min_value=min_date, max_value=max_date)
        end_date   = st.date_input("End date",   value=max_date, min_value=min_date, max_value=max_date)
    else:
        days_map = {"1 Day": 1, "7 Days": 7, "10 Days": 10, "15 Days": 15, "30 Days": 30}
        n = days_map[filter_choice]
        end_date   = max_date
        start_date = max_date - timedelta(days=n - 1)

    st.markdown("---")
    if st.button("🔄 Refresh Data from Sheets"):
        st.cache_data.clear()
        st.rerun()

    st.markdown(
        "<span style='font-size:0.7rem;color:#6b7694;'>"
        "Live from Google Sheets<br>"
        "Auto-refreshes every 5 min<br><br>"
        "Excel &amp; Extraordinaire Offers</span>",
        unsafe_allow_html=True,
    )

# ─── FILTER DATA ──────────────────────────────────────────────────────────────
mask = (df_all["Date"].dt.date >= start_date) & (df_all["Date"].dt.date <= end_date)
df   = df_all[mask].copy()

if df.empty:
    st.warning("No data for the selected range. Please adjust the date filter.")
    st.stop()


# ─── WoW DATA PREP ────────────────────────────────────────────────────────────
# Always compare last 7 days vs the 7 days before that (from latest date in sheet)
wow_end        = df_all["Date"].max()
wow_start      = wow_end - timedelta(days=6)
prev_wow_end   = wow_start - timedelta(days=1)
prev_wow_start = prev_wow_end - timedelta(days=6)

df_this_week = df_all[
    (df_all["Date"] >= pd.Timestamp(wow_start)) &
    (df_all["Date"] <= pd.Timestamp(wow_end))
].copy().reset_index(drop=True)

df_prev_week = df_all[
    (df_all["Date"] >= pd.Timestamp(prev_wow_start)) &
    (df_all["Date"] <= pd.Timestamp(prev_wow_end))
].copy().reset_index(drop=True)

this_label = f"{wow_start.strftime('%d %b')} – {wow_end.strftime('%d %b %Y')}"
prev_label = f"{prev_wow_start.strftime('%d %b')} – {prev_wow_end.strftime('%d %b %Y')}"

def day_labels(d):
    return [f"Day {i+1}" for i in range(len(d))]


# ─── HEADER ───────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='font-family:Space Mono,monospace;font-size:1.4rem;"
    "letter-spacing:-0.5px;margin-bottom:2px;'>📊 Offers Performance Dashboard</h1>"
    "<p style='color:#6b7694;font-size:0.78rem;text-transform:uppercase;"
    "letter-spacing:0.8px;margin-bottom:0;'>Excel &amp; Extraordinaire · Live from Google Sheets</p>",
    unsafe_allow_html=True,
)
st.markdown("---")


# ─── SECTION 1: METRICS ───────────────────────────────────────────────────────
st.markdown("<div class='section-header'>📌 Total Metrics for Selected Period</div>", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Excel Activations",           f"{int(df['Excel Activations'].sum()):,}")
c2.metric("Excel Redemptions",           f"{int(df['Excel Redemptions'].sum()):,}")
c3.metric("Extraordinaire Activations",  f"{int(df['Extraordinaire Activations'].sum()):,}")
c4.metric("Extraordinaire Redemptions",  f"{int(df['Extraordinaire Redemptions'].sum()):,}")

c5, c6, c7, c8 = st.columns(4)
c5.metric("Unique Shoppers (Total)", f"{int(df['Unique Shoppers'].sum()):,}")
c6.metric("Avg Unique Shoppers/Day", f"{df['Unique Shoppers'].mean():.1f}")
c7.metric("Total Cashback Spent",    f"₹{df['Cashback Amount'].sum():.2f}")
c8.metric("Avg Cashback/Day",        f"₹{df['Cashback Amount'].mean():.2f}")

st.markdown("---")


# ─── SECTION 2: ACTIVATIONS COMPARISON ───────────────────────────────────────
st.markdown("<div class='section-header'>🔵 Activations Comparison</div>", unsafe_allow_html=True)

fig_act = go.Figure()
fig_act.add_trace(go.Scatter(
    x=df["Date"], y=df["Excel Activations"],
    name="Excel Activations", mode="lines+markers",
    line=dict(color=C_EXCEL, width=2.5), marker=dict(size=4),
    fill="tozeroy", fillcolor="rgba(79,142,247,0.08)",
))
fig_act.add_trace(go.Scatter(
    x=df["Date"], y=df["Extraordinaire Activations"],
    name="Extraordinaire Activations", mode="lines+markers",
    line=dict(color=C_EXTRA, width=2.5), marker=dict(size=4),
    fill="tozeroy", fillcolor="rgba(247,113,79,0.08)",
))
fig_act.update_layout(
    **CHART_LAYOUT,
    title=dict(text="Excel vs Extraordinaire — Activations Over Time", font=dict(size=13, color="#e8ecf5"), x=0),
    yaxis_title="Activations", height=320,
)
st.plotly_chart(fig_act, use_container_width=True)


# ─── SECTION 3: REDEMPTIONS COMPARISON ───────────────────────────────────────
st.markdown("<div class='section-header'>🟠 Redemptions Comparison</div>", unsafe_allow_html=True)

fig_red = go.Figure()
fig_red.add_trace(go.Scatter(
    x=df["Date"], y=df["Excel Redemptions"],
    name="Excel Redemptions", mode="lines+markers",
    line=dict(color=C_EXCEL, width=2.5, dash="dot"), marker=dict(size=4),
))
fig_red.add_trace(go.Scatter(
    x=df["Date"], y=df["Extraordinaire Redemptions"],
    name="Extraordinaire Redemptions", mode="lines+markers",
    line=dict(color=C_EXTRA, width=2.5, dash="dot"), marker=dict(size=4),
))
fig_red.update_layout(
    **CHART_LAYOUT,
    title=dict(text="Excel vs Extraordinaire — Redemptions Over Time", font=dict(size=13, color="#e8ecf5"), x=0),
    yaxis_title="Redemptions", height=320,
)
st.plotly_chart(fig_red, use_container_width=True)


# ─── SECTION 4: UNIQUE SHOPPERS + CASHBACK ────────────────────────────────────
st.markdown("<div class='section-header'>🟢 Unique Shoppers & Cashback Trends</div>", unsafe_allow_html=True)

left, right = st.columns(2)

with left:
    fig_us = go.Figure()
    fig_us.add_trace(go.Scatter(
        x=df["Date"], y=df["Unique Shoppers"],
        name="Unique Shoppers", mode="lines+markers",
        line=dict(color=C_SHOPPERS, width=2.5), marker=dict(size=4),
        fill="tozeroy", fillcolor="rgba(247,212,79,0.10)",
    ))
    fig_us.update_layout(
        **CHART_LAYOUT,
        title=dict(text="Unique Shoppers Trend", font=dict(size=13, color="#e8ecf5"), x=0),
        yaxis_title="Unique Shoppers", height=300, showlegend=False,
    )
    st.plotly_chart(fig_us, use_container_width=True)

with right:
    fig_cb = go.Figure()
    fig_cb.add_trace(go.Scatter(
        x=df["Date"], y=df["Cashback Amount"],
        name="Cashback ₹", mode="lines+markers",
        line=dict(color=C_CASHBACK, width=2.5), marker=dict(size=4),
        fill="tozeroy", fillcolor="rgba(79,217,160,0.10)",
    ))
    fig_cb.update_layout(
        **CHART_LAYOUT,
        title=dict(text="Cashback Spend Trend (₹)", font=dict(size=13, color="#e8ecf5"), x=0),
        yaxis_title="Cashback ₹", yaxis_tickprefix="₹", height=300, showlegend=False,
    )
    st.plotly_chart(fig_cb, use_container_width=True)

st.markdown("---")


# ─── SECTION 5: WEEK-OVER-WEEK CHARTS ─────────────────────────────────────────
st.markdown(
    "<div class='section-header'>📆 Week-over-Week Comparison (Last 7 Days vs Previous 7 Days)</div>",
    unsafe_allow_html=True,
)

st.markdown(
    f"<div class='wow-info'>"
    f"<b style='color:#4f8ef7;'>● This week</b>: {this_label} &nbsp;&nbsp;|&nbsp;&nbsp; "
    f"<b style='color:#a78bfa;'>◆ Previous week</b>: {prev_label} (dashed)"
    f"</div>",
    unsafe_allow_html=True,
)

def wow_chart(title, col, y_title, line_color, y_prefix=""):
    """Overlaid WoW line chart — both series on a Day 1–7 x-axis."""
    fig = go.Figure()

    if not df_this_week.empty:
        fig.add_trace(go.Scatter(
            x=day_labels(df_this_week),
            y=df_this_week[col],
            name=f"This week ({this_label})",
            mode="lines+markers",
            line=dict(color=line_color, width=2.5),
            marker=dict(size=5),
            customdata=df_this_week["Date"].dt.strftime("%d %b"),
            hovertemplate="%{customdata}: %{y}<extra></extra>",
        ))

    if not df_prev_week.empty:
        fig.add_trace(go.Scatter(
            x=day_labels(df_prev_week),
            y=df_prev_week[col],
            name=f"Prev week ({prev_label})",
            mode="lines+markers",
            line=dict(color=C_PREV_WEEK, width=2, dash="dash"),
            marker=dict(size=5, symbol="diamond"),
            customdata=df_prev_week["Date"].dt.strftime("%d %b"),
            hovertemplate="%{customdata}: %{y}<extra></extra>",
        ))

    fig.update_layout(
        **CHART_LAYOUT,
        title=dict(text=title, font=dict(size=13, color="#e8ecf5"), x=0),
        yaxis_title=y_title,
        yaxis_tickprefix=y_prefix,
        xaxis_title="Day of week",
        height=280,
    )
    return fig


# Row 1 — Excel Activations | Extraordinaire Activations
r1l, r1r = st.columns(2)
with r1l:
    st.plotly_chart(wow_chart("Excel Activations — WoW", "Excel Activations", "Activations", C_EXCEL), use_container_width=True)
with r1r:
    st.plotly_chart(wow_chart("Extraordinaire Activations — WoW", "Extraordinaire Activations", "Activations", C_EXTRA), use_container_width=True)

# Row 2 — Excel Redemptions | Extraordinaire Redemptions
r2l, r2r = st.columns(2)
with r2l:
    st.plotly_chart(wow_chart("Excel Redemptions — WoW", "Excel Redemptions", "Redemptions", C_EXCEL), use_container_width=True)
with r2r:
    st.plotly_chart(wow_chart("Extraordinaire Redemptions — WoW", "Extraordinaire Redemptions", "Redemptions", C_EXTRA), use_container_width=True)

# Row 3 — Unique Shoppers | Cashback
r3l, r3r = st.columns(2)
with r3l:
    st.plotly_chart(wow_chart("Unique Shoppers — WoW", "Unique Shoppers", "Unique Shoppers", C_SHOPPERS), use_container_width=True)
with r3r:
    st.plotly_chart(wow_chart("Cashback Amount — WoW", "Cashback Amount", "Cashback ₹", C_CASHBACK, y_prefix="₹"), use_container_width=True)


# ─── SECTION 6: WoW DELTA SUMMARY ────────────────────────────────────────────
st.markdown("<div class='section-header'>📊 Week-over-Week Delta Summary</div>", unsafe_allow_html=True)

def wow_delta(col, prefix="", decimals=0):
    this_val = df_this_week[col].sum() if not df_this_week.empty else 0
    prev_val = df_prev_week[col].sum() if not df_prev_week.empty else 0
    diff = this_val - prev_val
    pct  = (diff / prev_val * 100) if prev_val != 0 else 0
    sign = "+" if diff >= 0 else ""
    if decimals:
        val_str   = f"{prefix}{this_val:.{decimals}f}"
        delta_str = f"{sign}{prefix}{diff:.{decimals}f} ({sign}{pct:.1f}%)"
    else:
        val_str   = f"{prefix}{int(this_val):,}"
        delta_str = f"{sign}{prefix}{int(diff):,} ({sign}{pct:.1f}%)"
    return val_str, delta_str

d1, d2, d3, d4 = st.columns(4)
v, delta = wow_delta("Excel Activations");            d1.metric("Excel Activations",           v, delta)
v, delta = wow_delta("Excel Redemptions");            d2.metric("Excel Redemptions",            v, delta)
v, delta = wow_delta("Extraordinaire Activations");   d3.metric("Extraordinaire Activations",   v, delta)
v, delta = wow_delta("Extraordinaire Redemptions");   d4.metric("Extraordinaire Redemptions",   v, delta)

d5, d6, _, __ = st.columns(4)
v, delta = wow_delta("Unique Shoppers");              d5.metric("Unique Shoppers",  v, delta)
v, delta = wow_delta("Cashback Amount", "₹", 2);     d6.metric("Cashback Amount",  v, delta)

st.markdown("---")


# ─── SECTION 7: RAW DATA TABLE ────────────────────────────────────────────────
with st.expander("📋 View Raw Data for Selected Period"):
    display_df = df.copy()
    display_df["Date"] = display_df["Date"].dt.strftime("%d %b %Y")
    display_df["Cashback Amount"] = display_df["Cashback Amount"].apply(lambda x: f"₹{x:.2f}")
    st.dataframe(display_df.reset_index(drop=True), use_container_width=True)