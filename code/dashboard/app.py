"""Market intelligence dashboard for curated NSE Spark outputs."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
CURATED = ROOT / "dataset" / "processed" / "spark_output"
FINANCIALS = ROOT / "dataset" / "raw" / "company_master" / "india_quarterly_results_sample.csv"

st.set_page_config(page_title="NSE | Market intelligence", page_icon="◈", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
:root { --ink:#17231f; --muted:#73817b; --green:#087e62; --line:#e7ece8; --canvas:#f6f8f6; }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
.stApp { background:var(--canvas); color:var(--ink); }
.block-container { max-width:1440px; padding-top:2rem; padding-bottom:3rem; }
[data-testid="stSidebar"] { background:#fff; border-right:1px solid var(--line); }
[data-testid="stSidebar"] > div:first-child { padding-top:1.6rem; }
[data-testid="stSidebar"] [data-testid="stRadio"] label { padding: .35rem 0; font-weight:500; }
h1,h2,h3 { font-family:'Manrope',sans-serif!important; letter-spacing:-.035em!important; color:var(--ink)!important; }
h1 { font-size:2.25rem!important; font-weight:800!important; margin-bottom:.15rem!important; }
h2 { font-size:1.45rem!important; font-weight:750!important; }
h3 { font-size:1.05rem!important; font-weight:700!important; }
p, .stCaption { color:var(--muted); }
[data-testid="stMetric"] { background:#fff; padding:1.15rem 1.25rem; border:1px solid var(--line); border-radius:14px; box-shadow:0 3px 12px rgba(20,50,38,.025); }
[data-testid="stMetricLabel"] { color:#718078; font-size:.79rem; font-weight:600; }
[data-testid="stMetricValue"] { font-family:'Manrope',sans-serif; font-size:1.65rem; font-weight:750; color:#17231f; }
[data-testid="stMetricDelta"] { font-size:.78rem; }
[data-testid="stPlotlyChart"] { background:#fff; border:1px solid var(--line); border-radius:15px; padding:8px 10px 2px; box-shadow:0 3px 12px rgba(20,50,38,.025); }
[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:12px; overflow:hidden; }
.eyebrow { color:#0b8064; text-transform:uppercase; letter-spacing:.14em; font-size:.68rem; font-weight:700; margin-bottom:.55rem; }
.hero { background:linear-gradient(115deg,#102e28 0%,#124e40 65%,#14745a 100%); padding:2rem 2.25rem; border-radius:20px; color:#fff; margin:0 0 1.25rem; position:relative; overflow:hidden; }
.hero:after { content:''; position:absolute; width:280px;height:280px;border:1px solid rgba(255,255,255,.14);border-radius:50%;right:6%;top:-155px;box-shadow:0 0 0 35px rgba(255,255,255,.035),0 0 0 72px rgba(255,255,255,.025); }
.hero h1 { color:#fff!important; font-size:2.05rem!important; margin:0!important; }
.hero p { color:#c2d8d0; margin:.45rem 0 0; font-size:.94rem; }
.hero .eyebrow { color:#81d9bc; }
.section-head { display:flex; align-items:end; justify-content:space-between; margin:1.6rem 0 .8rem; }
.section-head p { margin:0; font-size:.82rem; }
.pill { display:inline-block; background:#e3f3ed; color:#087e62; border-radius:20px; padding:5px 10px; font-size:.72rem; font-weight:700; }
div[data-testid="stSelectbox"] label, div[data-testid="stMultiSelect"] label { color:#53635b; font-weight:600; }
button[kind="secondary"] { border-radius:9px; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner="Loading curated market data…")
def read_table(name: str) -> pd.DataFrame:
    path = CURATED / name
    return pd.read_parquet(path) if path.exists() else pd.DataFrame()


@st.cache_data(show_spinner="Scanning selected price history…")
def read_prices(symbols: tuple[str, ...], ymin: int, ymax: int) -> pd.DataFrame:
    import pyarrow.dataset as ds
    path = CURATED / "prices_clean"
    if not path.exists() or not symbols:
        return pd.DataFrame()
    dataset = ds.dataset(path, format="parquet", partitioning="hive")
    filt = ds.field("symbol").isin(list(symbols)) & (ds.field("year") >= ymin) & (ds.field("year") <= ymax)
    columns = [c for c in ("date", "symbol", "series", "close", "volume", "daily_return", "year") if c in dataset.schema.names]
    return dataset.to_table(columns=columns, filter=filt).to_pandas()


def chart(fig, height: int = 350):
    fig.update_layout(
        height=height, margin=dict(l=12, r=16, t=52, b=12),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color="#53635b", size=11),
        title=dict(font=dict(family="Manrope, sans-serif", size=15, color="#17231f"), x=.025, y=.97),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=.98, title=None),
        hoverlabel=dict(bgcolor="#102e28", font_color="white"),
    )
    fig.update_xaxes(showgrid=False, linecolor="#e7ece8", tickfont=dict(color="#7b8982"))
    fig.update_yaxes(showgrid=True, gridcolor="#edf1ee", zeroline=False, tickfont=dict(color="#7b8982"))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def section(title: str, note: str = ""):
    st.markdown(f'<div class="section-head"><div><h3 style="margin:0">{title}</h3><p>{note}</p></div></div>', unsafe_allow_html=True)


stock = read_table("stock_summary")
yearly = read_table("yearly_summary")
monthly = read_table("monthly_summary")
daily = read_table("daily_market_summary")

st.sidebar.markdown('<div class="eyebrow">NSE · DATA TERMINAL</div>', unsafe_allow_html=True)
st.sidebar.markdown("## ◈ MarketLens")
st.sidebar.caption("Historical market analytics · Spark local mode")
st.sidebar.markdown("---")
page = st.sidebar.radio("WORKSPACE", ["Market Overview", "Stock Explorer", "Market Trends", "Company Fundamentals", "Correlation & Risk", "Data Quality & Pipeline"], label_visibility="visible")
st.sidebar.markdown("---")
if stock.empty:
    st.warning("Curated data is not available. Run `python code/processing/nse_spark_analysis.py` first.")
    st.stop()

series = sorted(stock.series.dropna().unique())
selected_series = st.sidebar.multiselect("Trading series", series, default=series)
universe = stock[stock.series.isin(selected_series)]
if universe.empty:
    st.info("Select at least one trading series in the sidebar.")
    st.stop()

if page == "Market Overview":
    latest = pd.to_datetime(daily.date, errors="coerce").max() if not daily.empty else pd.NaT
    latest_label = latest.strftime("%d %b %Y") if pd.notna(latest) else "CURATED HISTORY"
    st.markdown(f'''<div class="hero"><div class="eyebrow">MARKET PULSE · {latest_label}</div><h1>See the market in context.</h1><p>One clear view of NSE price history, liquidity, and market breadth.</p></div>''', unsafe_allow_html=True)
    active_daily = daily[daily.series.isin(selected_series)] if not daily.empty else daily
    obs = int(yearly[yearly.series.isin(selected_series)].total_records.sum()) if not yearly.empty else int(universe.trading_days.sum())
    sessions = int(active_daily.date.nunique()) if not active_daily.empty else 0
    date_min = pd.to_datetime(active_daily.date, errors="coerce").min() if sessions else pd.NaT
    date_max = pd.to_datetime(active_daily.date, errors="coerce").max() if sessions else pd.NaT
    k = st.columns(4)
    k[0].metric("Price observations", f"{obs:,}", help="Curated daily price rows in the selected series")
    k[1].metric("Listed symbols", f"{universe.symbol.nunique():,}", help="Symbols represented in the selected trading series")
    k[2].metric("Trading sessions", f"{sessions:,}")
    k[3].metric("History covered", f"{date_min:%Y} — {date_max:%Y}" if sessions else "—")
    section("Market activity", "Annual coverage and trading volume across the selected series")
    left, right = st.columns([1, 1])
    if not yearly.empty:
        view = yearly[yearly.series.isin(selected_series)].copy()
        left.plotly_chart(px.area(view, x="year", y="total_records", color="series", markers=True, title="Daily observations by year", color_discrete_sequence=["#087e62", "#68b89d", "#d6a75d"]).update_traces(line_width=2, fill="tozeroy", opacity=.18), use_container_width=True)
        right.plotly_chart(px.bar(view, x="year", y="total_volume", color="series", barmode="stack", title="Traded volume by year", color_discrete_sequence=["#087e62", "#68b89d", "#d6a75d"]), use_container_width=True)
    if not active_daily.empty:
        section("Market breadth", "Number of symbols trading on each market date")
        fig = px.line(active_daily, x="date", y="active_symbols", color="series", title="Active symbols over time", color_discrete_sequence=["#087e62", "#d6a75d", "#6489a6"])
        fig.update_traces(line_width=2)
        chart(fig, 310)
    st.caption("Source: curated NSE daily history processed with Spark. Closing prices are unadjusted.")

elif page == "Stock Explorer":
    st.markdown('<div class="eyebrow">SINGLE SECURITY</div>', unsafe_allow_html=True)
    st.title("Stock Explorer")
    st.caption("Inspect long term price behaviour and trading activity for a listed symbol.")
    symbol = st.selectbox("Symbol", sorted(universe.symbol.unique()))
    stock_rows = universe[universe.symbol == symbol].sort_values("series")
    stock_series = st.selectbox("Trading series", stock_rows.series.tolist())
    row = stock_rows[stock_rows.series == stock_series].iloc[0]
    y0, y1 = pd.to_datetime(row.first_date).year, pd.to_datetime(row.last_date).year
    years = st.slider("History window", int(y0), int(y1), (int(y0), int(y1))) if y1 > y0 else (int(y0), int(y1))
    hist = read_prices((symbol,), *years)
    hist = hist[hist.series == stock_series].sort_values("date")
    m = st.columns(4)
    m[0].metric("Latest close", f"₹{row.latest_close:,.2f}")
    m[1].metric("Period price return", f"{row.period_price_return:.1%}" if pd.notna(row.period_price_return) else "—")
    m[2].metric("Annualized volatility", f"{row.annualized_volatility:.1%}" if pd.notna(row.annualized_volatility) else "—")
    m[3].metric("Trading sessions", f"{int(row.trading_days):,}")
    if not hist.empty:
        fig = px.line(hist, x="date", y="close", title=f"{symbol} · closing price", color_discrete_sequence=["#087e62"])
        fig.update_traces(line_width=2)
        chart(fig, 390)
        chart(px.bar(hist, x="date", y="volume", title="Daily traded volume", color_discrete_sequence=["#83b9a6"]), 270)
    else:
        st.info("No price observations for this symbol in the selected window.")

elif page == "Market Trends":
    st.markdown('<div class="eyebrow">LIQUIDITY & PARTICIPATION</div>', unsafe_allow_html=True)
    st.title("Market Trends")
    st.caption("Follow monthly trading activity across the selected NSE series.")
    if monthly.empty:
        st.info("Monthly summary is not available.")
    else:
        trend = monthly[monthly.series.isin(selected_series)].copy()
        trend.month_start = pd.to_datetime(trend.month_start)
        a, b = st.columns(2)
        a.plotly_chart(px.area(trend, x="month_start", y="total_volume", color="series", title="Monthly traded volume", color_discrete_sequence=["#087e62", "#d6a75d", "#638aa2"]), use_container_width=True)
        b.plotly_chart(px.line(trend, x="month_start", y="active_symbols", color="series", title="Active symbols per month", markers=True, color_discrete_sequence=["#087e62", "#d6a75d", "#638aa2"]), use_container_width=True)
        section("Monthly records", "Latest periods first")
        st.dataframe(trend.sort_values("month_start", ascending=False), use_container_width=True, hide_index=True)

elif page == "Company Fundamentals":
    st.markdown('<div class="eyebrow">QUARTERLY FILINGS</div>', unsafe_allow_html=True)
    st.title("Company Fundamentals")
    st.caption("Explore reported financials with their original reporting basis preserved.")
    if not FINANCIALS.exists():
        st.info("Quarterly financial sample was not found.")
    else:
        fin = pd.read_csv(FINANCIALS, low_memory=False)
        company = st.selectbox("Company", sorted(fin.company_name.dropna().unique()))
        part = fin[fin.company_name == company].copy()
        bases = sorted(part.basis.dropna().unique())
        basis = st.selectbox("Reporting basis", ["All available", *bases])
        if basis != "All available": part = part[part.basis == basis]
        part["quarter_end"] = pd.to_datetime(part.quarter_end, errors="coerce")
        a, b = st.columns(2)
        a.metric("Reported quarters", f"{part.quarter_end.nunique():,}")
        b.metric("Rows missing basis", f"{int(part.basis.isna().sum()):,}")
        metric = st.selectbox("Financial metric", ["revenue_inr", "net_profit_inr", "ebitda_inr"])
        chart(px.bar(part.sort_values("quarter_end"), x="quarter_end", y=metric, color="basis", title=f"{company} · {metric.replace('_', ' ')}", color_discrete_sequence=["#087e62", "#d6a75d"]), 360)
        st.caption("Coverage is uneven. Company names are not joined to NSE symbols; financial rows retain their reporting basis.")
        st.dataframe(part.sort_values("quarter_end", ascending=False), use_container_width=True, hide_index=True)

elif page == "Correlation & Risk":
    st.markdown('<div class="eyebrow">RETURNS & DISPERSION</div>', unsafe_allow_html=True)
    st.title("Correlation & Risk")
    st.caption("Compare co-movement and realized volatility using daily unadjusted close returns.")
    risk_series = st.selectbox("Trading series", selected_series)
    symbols = st.multiselect("Compare symbols", sorted(universe.symbol.unique()), default=sorted(universe.symbol.unique())[:5], max_selections=12)
    available = pd.to_numeric(yearly.year, errors="coerce").dropna().astype(int).unique() if not yearly.empty else []
    if len(symbols) >= 2 and len(available):
        lo, hi = int(min(available)), int(max(available))
        years = st.slider("Years", lo, hi, (max(lo, hi - 4), hi)) if hi > lo else (lo, hi)
        hist = read_prices(tuple(symbols), *years)
        hist = hist[hist.series == risk_series]
        returns = hist.pivot_table(index="date", columns="symbol", values="daily_return", aggfunc="mean")
        if returns.shape[1] >= 2:
            corr = returns.corr(min_periods=30)
            fig = px.imshow(corr, text_auto=".2f", color_continuous_scale=[[0, "#bd6659"], [.5, "#f4f5ef"], [1, "#087e62"]], zmin=-1, zmax=1, title="Daily return correlation")
            chart(fig, max(370, min(620, 180 + 38 * len(symbols))))
            risk = hist.groupby("symbol").daily_return.std().mul(252 ** .5).rename("annualized_volatility").reset_index().sort_values("annualized_volatility", ascending=False)
            chart(px.bar(risk, x="symbol", y="annualized_volatility", title="Annualized volatility · daily standard deviation × √252", color="annualized_volatility", color_continuous_scale=["#9fcbbb", "#087e62"]), 310)
        else:
            st.info("Not enough overlapping price observations for these selections.")
    else:
        st.info("Choose at least two symbols to compare.")
    st.caption("Returns use unadjusted closes and may reflect corporate actions. Correlations require overlapping observations.")

else:
    st.markdown('<div class="eyebrow">PIPELINE TRANSPARENCY</div>', unsafe_allow_html=True)
    st.title("Data Quality & Pipeline")
    st.caption("Inspect ETL checks and the coverage behind this dashboard.")
    report = CURATED / "quality_report.json"
    if report.exists():
        quality = json.loads(report.read_text(encoding="utf-8"))
        rows = pd.DataFrame([{"check": k.replace("_", " ").title(), "rows": v} for k, v in quality.items() if k.endswith("_rows") and isinstance(v, (int, float))])
        if not rows.empty:
            chart(px.bar(rows.sort_values("rows"), x="rows", y="check", orientation="h", title="Quality findings", color="rows", color_continuous_scale=["#a9cfc0", "#087e62"]), max(280, 34 * len(rows)))
        with st.expander("View full ETL run report"):
            st.json(quality)
    else:
        st.info("No quality report found. Run the Spark ETL first.")
    a, b = st.columns(2)
    with a:
        st.markdown("#### Execution")
        st.write("Spark `local[*]` on one machine. HDFS and YARN are not configured.")
    with b:
        st.markdown("#### Method")
        st.write("EQ, BE, and BZ retained. Zero volume retained. Returns use unadjusted close.")
    section("Coverage by symbol", "Longest price histories first")
    st.dataframe(universe.sort_values("trading_days", ascending=False), use_container_width=True, hide_index=True)
