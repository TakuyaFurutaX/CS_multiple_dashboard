import warnings
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import core
from core import ALL_CATEGORIES, TICKERS

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# McKinsey-style Theme
# ─────────────────────────────────────────────
MCK_NAVY    = "#051C2C"
MCK_BLUE    = "#2251FF"
MCK_TEAL    = "#027B8E"
MCK_GREY    = "#7F8C8D"
MCK_LGREY   = "#BDC3C7"
MCK_BG      = "#FFFFFF"
MCK_GRID    = "#ECF0F1"
MCK_TEXT    = "#2C3E50"

st.set_page_config(
    page_title="Consulting Valuation Monitor",
    page_icon="",
    layout="wide",
)

# Custom CSS — McKinsey aesthetic
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Main background */
    .stApp {
        background-color: #FAFBFC;
        font-family: 'Inter', 'Helvetica Neue', sans-serif;
    }

    /* Remove default padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }

    /* Headers */
    h1 {
        color: #051C2C !important;
        font-weight: 700 !important;
        font-size: 1.8rem !important;
        letter-spacing: -0.02em !important;
        border-bottom: 3px solid #2251FF;
        padding-bottom: 0.5rem;
        margin-bottom: 0.3rem !important;
    }
    h2, h3 {
        color: #051C2C !important;
        font-weight: 600 !important;
        letter-spacing: -0.01em !important;
    }
    .stSubheader, [data-testid="stMarkdownContainer"] h3 {
        font-size: 1.1rem !important;
        color: #051C2C !important;
        border-left: 3px solid #2251FF;
        padding-left: 0.8rem;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #051C2C !important;
    }
    [data-testid="stSidebar"] * {
        color: #ECF0F1 !important;
    }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stMultiSelect label,
    [data-testid="stSidebar"] .stCheckbox label,
    [data-testid="stSidebar"] .stSlider label {
        color: #BDC3C7 !important;
        font-size: 0.8rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        font-weight: 500 !important;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #FFFFFF !important;
        border-color: #2251FF !important;
        font-size: 0.9rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
    }

    /* Metric cards */
    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #ECF0F1;
        border-radius: 4px;
        padding: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    [data-testid="stMetric"] label {
        color: #7F8C8D !important;
        font-size: 0.75rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #051C2C !important;
        font-weight: 700 !important;
    }

    /* Tables */
    .stDataFrame {
        border: 1px solid #ECF0F1;
        border-radius: 4px;
    }

    /* Info/Warning/Error boxes */
    .stAlert {
        border-radius: 4px;
        border-left: 4px solid;
        font-size: 0.85rem;
    }

    /* Caption text */
    .stCaption, [data-testid="stCaptionContainer"] {
        color: #7F8C8D !important;
        font-size: 0.75rem !important;
        letter-spacing: 0.02em !important;
    }

    /* Divider */
    hr {
        border-color: #ECF0F1 !important;
    }

    /* Sidebar inputs: 背景と文字色を両方固定（ライト/ダークテーマどちらでも読める） */
    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] .stSelectbox [role="group"] {
        background-color: #0E3246 !important;
        border-color: #2A5670 !important;
    }
    [data-testid="stSidebar"] [data-baseweb="select"] *,
    [data-testid="stSidebar"] .stSelectbox [role="group"] * {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] .stButton button {
        background-color: #0E3246 !important;
        border: 1px solid #2A5670 !important;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        border-color: #2251FF !important;
    }

    /* Sidebar expanders */
    [data-testid="stSidebar"] [data-testid="stExpander"] {
        border-color: #1B3A4B !important;
        background-color: transparent !important;
    }

    /* Spinner */
    .stSpinner > div {
        border-top-color: #2251FF !important;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Color palette per category（平均線 + 個別銘柄の濃淡）
# ─────────────────────────────────────────────
CATEGORY_AVG_COLORS = {
    "米国コンサル":         MCK_BLUE,
    "グローバルITサービス": "#6A3FB5",
    "日本コンサル":         MCK_TEAL,
    "AI系":               MCK_NAVY,
}
CATEGORY_SHADES = {
    "米国コンサル":         ["#7BAFD4", "#A3C4DC", "#6B9CC4", "#4A7DA4", "#8FB8D8", "#5A8DB4", "#3D6FA0", "#9DBFE0", "#2F5F8F"],
    "グローバルITサービス": ["#9C8BCB", "#8570B8", "#B3A6DB", "#7A62AE", "#A89AD2", "#6F55A3", "#C4B9E3"],
    "日本コンサル":         ["#4A9F8D", "#6BBFAD", "#9C9485", "#8ED0C1", "#5AAF9D", "#C4BDB0", "#3B8A7A",
                            "#7FB8A8", "#B7A98F", "#A6CFC4", "#8C8575", "#2E7F6E", "#D4CDBF"],
    "AI系":               ["#6B8DB5", "#5A7DA5", "#4A6D95", "#8FA8C8", "#3A5D85", "#A3B8D4", "#7C98BC"],
}

# ─────────────────────────────────────────────
# Plotly template — McKinsey style
# ─────────────────────────────────────────────
MCK_LAYOUT = dict(
    font=dict(family="Inter, Helvetica Neue, sans-serif", color=MCK_TEXT, size=12),
    paper_bgcolor=MCK_BG,
    plot_bgcolor=MCK_BG,
    title=dict(font=dict(size=14, color=MCK_NAVY), x=0, xanchor="left"),
    xaxis=dict(
        gridcolor=MCK_GRID, gridwidth=1,
        linecolor=MCK_LGREY, linewidth=1,
        tickfont=dict(size=10, color=MCK_GREY),
        title_font=dict(size=11, color=MCK_GREY),
        showgrid=True,
    ),
    yaxis=dict(
        gridcolor=MCK_GRID, gridwidth=1,
        linecolor=MCK_LGREY, linewidth=1,
        tickfont=dict(size=10, color=MCK_GREY),
        title_font=dict(size=11, color=MCK_GREY),
        zeroline=False,
        showgrid=True,
    ),
    legend=dict(
        font=dict(size=10, color=MCK_TEXT),
        bgcolor="rgba(255,255,255,0.9)",
        bordercolor=MCK_GRID,
        borderwidth=1,
    ),
    hoverlabel=dict(
        bgcolor=MCK_NAVY,
        font_color="white",
        font_size=11,
        font_family="Inter, Helvetica Neue, sans-serif",
    ),
    margin=dict(l=50, r=20, t=50, b=40),
)

PERIOD_DAYS = {"1y": 365, "2y": 730, "3y": 1095, "5y": 1825}


def _rgba(hex_color, alpha):
    return f"rgba({int(hex_color[1:3], 16)},{int(hex_color[3:5], 16)},{int(hex_color[5:7], 16)},{alpha})"


# ─────────────────────────────────────────────
# Data（キャッシュ読込 → 古い部分だけAPI更新）
# ─────────────────────────────────────────────
@st.cache_data(ttl=6 * 3600, show_spinner="Updating market data...")
def load_data():
    tickers = list(TICKERS)
    warnings_ = []
    try:
        prices = core.update_prices(tickers)
    except Exception as e:
        prices = core.load_prices()
        warnings_.append(f"株価の更新に失敗したためキャッシュを表示しています ({type(e).__name__})")
    try:
        fund, failed = core.update_fundamentals(tickers)
        if failed:
            warnings_.append("EPSの更新に失敗（前回値を使用）: " + ", ".join(failed))
    except Exception as e:
        fund = core.load_fundamentals()
        warnings_.append(f"EPSの更新に失敗したためキャッシュを表示しています ({type(e).__name__})")
    return prices, fund, warnings_


prices, fund, load_warnings = load_data()
fx = fund.get("fx", {})

# 時価総額（USD換算）順にカテゴリ内ソート
def _mcap(t):
    return core.usd_market_cap(fund["data"].get(t, {}), fx) or 0

ordered = sorted(TICKERS, key=lambda t: (ALL_CATEGORIES.index(TICKERS[t]["category"]), -_mcap(t)))
colors = {}
for cat in ALL_CATEGORIES:
    shades = CATEGORY_SHADES[cat]
    for i, t in enumerate([t for t in ordered if TICKERS[t]["category"] == cat]):
        colors[t] = shades[i % len(shades)]

# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
as_of = prices.index.max().strftime("%Y-%m-%d") if not prices.empty else "n/a"
st.title("Consulting Valuation Monitor")
st.caption(f"Global & Japan consulting / IT services  |  AI disruption tracking  |  Data as of {as_of}")
for w in load_warnings:
    st.warning(w)

# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────
st.sidebar.markdown("### PARAMETERS")
period = st.sidebar.selectbox("PERIOD", list(PERIOD_DAYS), index=1)
agg_label = st.sidebar.selectbox("CATEGORY AVERAGE", ["Median", "Mean"], index=0)
agg_how = agg_label.lower()
per_cap = st.sidebar.slider(
    "PER CAP (outlier)", 50, 500, 200, step=25,
    help="これを超えるPERは利益が極小の特殊期間とみなし、チャート・平均から除外",
)
log_scale = st.sidebar.checkbox("Log scale", value=True)
show_forecast = st.sidebar.checkbox("Show forecast", value=True)
forecast_days = st.sidebar.slider("Forecast days", 180, 360, 180, step=30)

if st.sidebar.button("Refresh data"):
    load_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### TICKERS")
active = []
for cat in ALL_CATEGORIES:
    with st.sidebar.expander(cat, expanded=False):
        for t in [t for t in ordered if TICKERS[t]["category"] == cat]:
            if st.checkbox(TICKERS[t]["name"], value=True, key=f"chk_{t}"):
                active.append(t)

# ─────────────────────────────────────────────
# PER series
# ─────────────────────────────────────────────
cutoff = pd.Timestamp.now().normalize() - pd.Timedelta(days=PERIOD_DAYS[period])
per_full = {}   # 全期間（KPIの前年比用）
per_view = {}   # 表示期間
no_data = []
for t in active:
    f = fund["data"].get(t)
    if t not in prices.columns or not f:
        no_data.append(TICKERS[t]["name"])
        continue
    s = core.per_series(prices[t], f.get("eps_points"), TICKERS[t].get("exclude_eps", ()))
    s = s.where(s <= per_cap)
    per_full[t] = s
    per_view[t] = s[s.index >= cutoff]  # NaNは残す（除外期間を線でつながない）

cat_full = {
    cat: core.category_aggregate([per_full[t].dropna() for t in per_full if TICKERS[t]["category"] == cat], agg_how)
    for cat in ALL_CATEGORIES
}
cat_view = {cat: s[s.index >= cutoff] for cat, s in cat_full.items()}

# ─────────────────────────────────────────────
# KPI row
# ─────────────────────────────────────────────
kpi_cols = st.columns(len(ALL_CATEGORIES))
for col, cat in zip(kpi_cols, ALL_CATEGORIES):
    s = cat_full[cat]
    if s.empty:
        col.metric(f"{cat} ({agg_label})", "n/a")
        continue
    now = s.iloc[-1]
    prev = s[s.index <= s.index[-1] - pd.DateOffset(years=1)]
    delta = f"{now - prev.iloc[-1]:+.1f}x vs 1y ago" if not prev.empty else None
    n = sum(1 for t in per_full if TICKERS[t]["category"] == cat and not per_full[t].dropna().empty)
    col.metric(f"{cat} ({agg_label} PER)", f"{now:.1f}x", delta, help=f"PERを算出できた {n} 銘柄の{agg_label}")

# ─────────────────────────────────────────────
# Main Chart
# ─────────────────────────────────────────────
fig = go.Figure()
fig.update_layout(**MCK_LAYOUT)

# --- Avg線を先に追加（凡例の先頭に表示） ---
for cat in ALL_CATEGORIES:
    s = cat_view[cat]
    if s.empty:
        continue
    avg_color = CATEGORY_AVG_COLORS[cat]
    fig.add_trace(go.Scatter(
        x=s.index, y=s.values,
        mode="lines",
        name=f"{agg_label}: {cat}",
        line=dict(color=avg_color, width=3.5),
        legendgroup=cat,
        legendgrouptitle_text=cat,
        hovertemplate=f"{agg_label}: {cat}<br>%{{x|%Y-%m-%d}}<br>PER: %{{y:.1f}}x<extra></extra>",
    ))

    if show_forecast:
        fc = core.forecast_trend(s, forecast_days)
        if fc is not None:
            fdates, f_center, f_upper, f_lower = fc
            fig.add_trace(go.Scatter(
                x=fdates, y=f_upper, mode="lines", line=dict(width=0),
                legendgroup=cat, showlegend=False, hoverinfo="skip",
            ))
            fig.add_trace(go.Scatter(
                x=fdates, y=f_lower, mode="lines", line=dict(width=0),
                fill="tonexty", fillcolor=_rgba(avg_color, 0.12),
                legendgroup=cat, showlegend=False, hoverinfo="skip",
            ))
            fig.add_trace(go.Scatter(
                x=fdates, y=f_center,
                mode="lines",
                name=f"Forecast: {cat}",
                line=dict(color=avg_color, width=2.5, dash="dot"),
                opacity=0.8,
                legendgroup=cat, showlegend=False,
                hovertemplate=f"Forecast: {cat}<br>%{{x|%Y-%m-%d}}<br>PER: %{{y:.1f}}x<extra></extra>",
            ))

# --- 個別銘柄を後に追加 ---
for t in ordered:
    s = per_view.get(t)
    if s is None or s.dropna().empty:
        continue
    meta = TICKERS[t]
    fig.add_trace(go.Scatter(
        x=s.index, y=s.values,
        mode="lines",
        name=meta["name"],
        line=dict(color=colors[t], width=1.2),
        opacity=0.35,
        legendgroup=meta["category"],
        hovertemplate=f"{meta['name']}<br>%{{x|%Y-%m-%d}}<br>PER: %{{y:.1f}}x<extra></extra>",
    ))

fig.update_layout(
    height=640,
    title=dict(text=f"Trailing PER  —  Daily trend with category {agg_label.lower()}s"),
    yaxis=dict(
        type="log" if log_scale else "linear", title="PER (x)",
        tickvals=[5, 10, 15, 20, 30, 50, 100, 200, 300, 500] if log_scale else None,
    ),
    legend=dict(
        orientation="v", y=1, x=1.02,
        groupclick="togglegroup",
        traceorder="grouped",
    ),
    hovermode="x unified",
)
st.plotly_chart(fig, width="stretch", key="main_chart")

st.markdown(
    f'<div style="color:{MCK_TEXT}; font-size:0.72rem; line-height:1.6; margin-top:-0.5rem;">'
    f'* Trailing PER = 終値 ÷ 直近実績EPS（決算発表日以降に反映） &ensp;|&ensp; '
    f'赤字期間・PER&gt;{per_cap}x は除外 &ensp;|&ensp; '
    f'Forecast: 表示期間の対数PERトレンドを延長、帯は ±2σ（日次対数変化のσ × √t）。予測ではなく単純な外挿'
    f'</div>',
    unsafe_allow_html=True,
)
if no_data:
    st.caption("データ取得不可: " + ", ".join(no_data))

# ─────────────────────────────────────────────
# Summary table
# ─────────────────────────────────────────────
st.markdown("### Snapshot")
rows = []
for t in ordered:
    if t not in active or t not in per_full:
        continue
    meta, f = TICKERS[t], fund["data"][t]
    price = prices[t].dropna()
    raw_per = core.per_series(prices[t], f.get("eps_points"), meta.get("exclude_eps", ())).dropna()
    view = per_view[t].dropna()
    last_eps = (f.get("eps_points") or [[None, None]])[-1][1]
    fwd = f.get("forward_eps")
    cur_per = raw_per.iloc[-1] if not raw_per.empty and raw_per.index[-1] == price.index[-1] else np.nan
    pct_rank = (view <= view.iloc[-1]).mean() * 100 if not view.empty and not np.isnan(cur_per) else np.nan
    rows.append({
        "銘柄": meta["name"],
        "Ticker": t,
        "カテゴリ": meta["category"],
        "時価総額 ($bn)": (_mcap(t) or np.nan) / 1e9,
        "実績PER": cur_per,
        "予想PER": price.iloc[-1] / fwd if fwd and fwd > 0 else np.nan,
        "期間高値": view.max() if not view.empty else np.nan,
        "期間安値": view.min() if not view.empty else np.nan,
        "高値比 (%)": (cur_per / view.max() - 1) * 100 if not view.empty and not np.isnan(cur_per) else np.nan,
        "期間内位置 (%)": pct_rank,
        "状態": ("赤字" if last_eps is not None and last_eps <= 0
                 else "一過性要因で除外" if (f.get("eps_points") or [[None]])[-1][0] in meta.get("exclude_eps", ())
                 else "PER上限超" if cur_per > per_cap else ""),
    })
summary = pd.DataFrame(rows)
if not summary.empty:
    st.dataframe(
        summary,
        hide_index=True,
        width="stretch",
        column_config={
            "時価総額 ($bn)": st.column_config.NumberColumn(format="%.1f"),
            "実績PER": st.column_config.NumberColumn(format="%.1fx"),
            "予想PER": st.column_config.NumberColumn(format="%.1fx", help="会社予想（日本株: IRBank）/ アナリスト予想（その他: Yahoo）"),
            "期間高値": st.column_config.NumberColumn(format="%.1fx"),
            "期間安値": st.column_config.NumberColumn(format="%.1fx"),
            "高値比 (%)": st.column_config.NumberColumn(format="%.1f"),
            "期間内位置 (%)": st.column_config.ProgressColumn(
                min_value=0, max_value=100, format="%.0f",
                help="表示期間のPER分布における現在値の位置（100=期間最高）"),
        },
    )
    near_high = summary[summary["高値比 (%)"] > -10]["銘柄"].tolist()
    near_low = summary[summary["期間内位置 (%)"] <= 10]["銘柄"].tolist()
    if near_high:
        st.info("期間高値から10%以内: " + ", ".join(near_high))
    if near_low:
        st.info("期間内で下位10%の水準: " + ", ".join(near_low))

with st.expander("Methodology & data sources"):
    st.markdown(
        f"""
- **株価**: Yahoo Finance 終値（分割調整済み・配当未調整）。過去{core.HISTORY_YEARS}年分を `data/prices.parquet` にキャッシュし、差分のみ更新。
- **EPS（米国・グローバル）**: Yahoo Finance の四半期 Reported EPS を直近4四半期で合算（TTM）し、決算発表日から反映。Capgemini は年次 Diluted EPS（期末+{core.ANNUAL_DISCLOSURE_LAG_DAYS}日から反映）。
- **EPS（日本株）**: IRBank の通期実績EPS。決算期末+{core.JP_DISCLOSURE_LAG_DAYS}日（決算短信の想定時期）から反映するため、年1回の階段状になります。
- **予想PER**: 日本株は IRBank の会社予想EPS、その他は Yahoo の forwardEps。
- **カテゴリ平均**: 各日で算出可能な銘柄の{agg_label}。上場・黒字化で構成銘柄が変わると不連続になり得ます。
- EPSは週1回、株価は6時間ごとに自動更新。`python scripts/update_data.py` で手動更新できます。
"""
    )
