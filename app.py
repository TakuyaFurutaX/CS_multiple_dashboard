import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
import requests
from bs4 import BeautifulSoup
import time
import warnings
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

    /* Spinner */
    .stSpinner > div {
        border-top-color: #2251FF !important;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# McKinsey color palette per category
# ─────────────────────────────────────────────
TICKERS = {
    # 米国コンサル — Blue tones
    "ACN":    {"name": "Accenture",           "category": "米国コンサル", "color": "#7BAFD4"},
    "BAH":    {"name": "Booz Allen Hamilton",  "category": "米国コンサル", "color": "#A3C4DC"},
    "FCN":    {"name": "FTI Consulting",      "category": "米国コンサル", "color": "#6B9CC4"},
    "HURN":   {"name": "Huron Consulting",    "category": "米国コンサル", "color": "#8FB8D8"},
    "ICFI":   {"name": "ICF International",   "category": "米国コンサル", "color": "#5A8DB4"},
    "KFY":    {"name": "Korn Ferry",          "category": "米国コンサル", "color": "#4A7DA4"},
    # 日本コンサル — Teal tones
    "4307.T": {"name": "野村総研(NRI)",        "category": "日本コンサル", "color": "#4A9F8D"},
    "6532.T": {"name": "ベイカレント",         "category": "日本コンサル", "color": "#6BBFAD"},
    "6088.T": {"name": "シグマクシス",         "category": "日本コンサル", "color": "#8ED0C1"},
    "4310.T": {"name": "ドリームインキュベータ", "category": "日本コンサル", "color": "#5AAF9D"},
    "9168.T": {"name": "ライズコンサルティング", "category": "日本コンサル", "color": "#C4BDB0"},
    "277A.T": {"name": "グロービング",         "category": "日本コンサル", "color": "#9C9485"},
    # AI系 — Navy/Dark tones
    "4259.T": {"name": "エクサウィザーズ",      "category": "AI系",       "color": "#6B8DB5"},
    "AI":     {"name": "C3.ai",               "category": "AI系",       "color": "#5A7DA5"},
}

CATEGORY_AVG_COLORS = {
    "米国コンサル": MCK_BLUE,
    "日本コンサル": MCK_TEAL,
    "AI系":       MCK_NAVY,
}

ALL_CATEGORIES = ["米国コンサル", "日本コンサル", "AI系"]
FORECAST_DAYS = 90

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

# ─────────────────────────────────────────────
# Data
# ─────────────────────────────────────────────
def _parse_irbank_value(s):
    """IRBankの日本語単位付き数値をパース"""
    s = s.replace(",", "").replace("+", "").replace("%", "").strip()
    if s == "-" or s == "":
        return None
    if "億" in s:
        return float(s.replace("億", "")) * 1e8
    elif "百万" in s:
        return float(s.replace("百万", "")) * 1e6
    elif "千" in s:
        return float(s.replace("千", "")) * 1e3
    return float(s)


@st.cache_data(ttl=86400)
def fetch_irbank(code):
    """IRBankから予想EPS・純資産を取得"""
    try:
        url = f"https://irbank.net/{code}/results"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        tables = soup.find_all("table")

        forecast_eps, net_income, net_assets = None, None, None

        # Table 0: 業績 → ヘッダーからEPS列を特定し予想EPSを取得
        if len(tables) > 0:
            rows = tables[0].find_all("tr")
            header = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]
            eps_idx = None
            for i, h in enumerate(header):
                if h == "EPS":
                    eps_idx = i
                    break

            for row in reversed(rows[1:]):
                cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
                # 予想行からEPS取得
                if "予" in cells[0] and eps_idx and len(cells) > eps_idx:
                    try:
                        forecast_eps = float(cells[eps_idx].replace(",", ""))
                    except (ValueError, TypeError):
                        pass
                    break

            # 実績の純利益（フォールバック用）
            for row in reversed(rows[1:]):
                cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
                if "予" not in cells[0] and len(cells) > 4:
                    val = _parse_irbank_value(cells[4])
                    if val is not None:
                        net_income = val
                        break

        # Table 1: 財務 → 純資産(col 2)
        if len(tables) > 1:
            for row in reversed(tables[1].find_all("tr")[1:]):
                cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
                if len(cells) > 2:
                    val = _parse_irbank_value(cells[2])
                    if val is not None:
                        net_assets = val
                        break
        return {"forecast_eps": forecast_eps, "net_income": net_income, "net_assets": net_assets}
    except Exception:
        return {}


import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
HIST_FILE = os.path.join(DATA_DIR, "history.parquet")
INFO_FILE = os.path.join(DATA_DIR, "info.json")


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _download_history(tickers_list, period="2y", start=None):
    """yf.downloadラッパー（リトライ付き）"""
    for attempt in range(3):
        try:
            kwargs = dict(group_by="ticker", progress=False)
            if start:
                kwargs["start"] = start
            else:
                kwargs["period"] = period
            data = yf.download(tickers_list, **kwargs)
            return data
        except Exception:
            if attempt < 2:
                time.sleep(3 * (attempt + 1))
    return None


def _save_history(data):
    _ensure_data_dir()
    data.to_parquet(HIST_FILE)


def _load_history():
    if os.path.exists(HIST_FILE):
        return pd.read_parquet(HIST_FILE)
    return None


def _save_info_cache(info_dict):
    _ensure_data_dir()
    with open(INFO_FILE, "w") as f:
        json.dump(info_dict, f, ensure_ascii=False, default=str)


def _load_info_cache():
    if os.path.exists(INFO_FILE):
        with open(INFO_FILE, "r") as f:
            return json.load(f)
    return {"data": {}, "dates": {}}


def fetch_all_history(tickers_list, period="2y"):
    """ローカルファイルから読み込み + 差分だけAPI取得"""
    cached = _load_history()

    if cached is not None and not cached.empty:
        last_date = cached.index[-1]
        today = pd.Timestamp.now().normalize()
        if last_date >= today:
            return cached
        # 差分だけ取得
        delta = _download_history(tickers_list, start=last_date.strftime("%Y-%m-%d"))
        if delta is not None and not delta.empty:
            combined = pd.concat([cached, delta])
            combined = combined[~combined.index.duplicated(keep="last")]
            combined.sort_index(inplace=True)
            _save_history(combined)
            return combined
        return cached

    # 初回: フル取得してファイルに保存
    data = _download_history(tickers_list, period=period)
    if data is not None and not data.empty:
        _save_history(data)
    return data


def _fetch_info_raw(ticker):
    """個別銘柄のinfo取得（リトライ付き）"""
    for attempt in range(3):
        try:
            return yf.Ticker(ticker).info
        except Exception:
            if attempt < 2:
                time.sleep(3 * (attempt + 1))
    return None


def fetch_info(ticker):
    """infoローカルキャッシュ（1日1回更新）"""
    if "info_cache" not in st.session_state:
        loaded = _load_info_cache()
        st.session_state["info_cache"] = loaded.get("data", {})
        st.session_state["info_dates"] = loaded.get("dates", {})

    today = datetime.now().strftime("%Y-%m-%d")
    if ticker in st.session_state["info_cache"] and st.session_state["info_dates"].get(ticker) == today:
        return st.session_state["info_cache"][ticker]

    info = _fetch_info_raw(ticker)
    if info:
        st.session_state["info_cache"][ticker] = info
        st.session_state["info_dates"][ticker] = today
        _save_info_cache({"data": st.session_state["info_cache"], "dates": st.session_state["info_dates"]})
    return info


def fetch_data_from_bulk(bulk_data, ticker):
    """一括データから個別銘柄を抽出し、infoと合わせて返す"""
    try:
        if bulk_data is None:
            return None, None
        if ticker in bulk_data.columns.get_level_values(0):
            hist = bulk_data[ticker].dropna(how="all")
        else:
            hist = bulk_data.dropna(how="all")
        if hist.empty:
            return None, None
    except Exception:
        return None, None

    info = fetch_info(ticker)
    if info is None:
        return None, None

    # 日本株: IRBankから予想EPSを取得（日本市場の標準PER = 予想ベース）
    if ticker.endswith(".T"):
        code = ticker.replace(".T", "")
        irbank = fetch_irbank(code)
        shares = info.get("sharesOutstanding")

        if irbank.get("forecast_eps"):
            info["trailingEps"] = irbank["forecast_eps"]
        elif not info.get("trailingEps") and shares and shares > 0 and irbank.get("net_income"):
            info["trailingEps"] = irbank["net_income"] / shares

        if not info.get("bookValue") and shares and shares > 0 and irbank.get("net_assets"):
            info["bookValue"] = irbank["net_assets"] / shares

    return hist, info


def compute_valuation_series(hist, info):
    df = hist[["Close"]].copy()
    df.columns = ["price"]

    trailing_eps = info.get("trailingEps")
    if trailing_eps and trailing_eps > 0:
        df["pe"] = df["price"] / trailing_eps
    else:
        df["pe"] = np.nan

    revenue_per_share = info.get("revenuePerShare")
    if revenue_per_share and revenue_per_share > 0:
        df["ps"] = df["price"] / revenue_per_share
    else:
        df["ps"] = np.nan

    ev_ebitda = info.get("enterpriseToEbitda")
    current_pe = info.get("trailingPE")
    if ev_ebitda and current_pe and current_pe > 0:
        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        if current_price and current_price > 0:
            df["ev_ebitda"] = ev_ebitda * (df["price"] / current_price)
        else:
            df["ev_ebitda"] = np.nan
    else:
        df["ev_ebitda"] = np.nan

    # 株価指数（初日=100に正規化）
    df["price_index"] = df["price"] / df["price"].iloc[0] * 100

    book_value = info.get("bookValue")
    if book_value and book_value > 0:
        df["pbr"] = df["price"] / book_value
    else:
        df["pbr"] = np.nan

    return df


def forecast_bb(series, days=FORECAST_DAYS):
    """予測: 生値の最終点から接続。傾き=全期間回帰、バンド=日次σ×√t"""
    clean = series.dropna()
    if len(clean) < 30:
        return None, None, None, None

    # 全期間で回帰 → 傾き
    X = np.arange(len(clean)).reshape(-1, 1)
    y = clean.values
    model = LinearRegression().fit(X, y)
    slope = model.coef_[0]

    # 日次リターンのσ（全期間）
    daily_returns = clean.pct_change().dropna()
    daily_sigma = daily_returns.std()

    # 生値の最終点から開始（チャートの平均線と接続）
    last_val = clean.iloc[-1]
    last_date = clean.index[-1]

    t = np.arange(0, days + 1)
    future_center = last_val + slope * t
    # t=0で幅0、√tで広がる（日次σ × √t × 2 × 現在値）
    band = 2 * daily_sigma * last_val * np.sqrt(t)
    future_upper = future_center + band
    future_lower = future_center - band

    future_dates = clean.index[-1:].append(
        pd.bdate_range(start=last_date + timedelta(days=1), periods=days)
    )
    return future_dates, future_center, future_upper, future_lower


# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
st.title("Consulting Valuation Monitor")
st.caption(f"Global & Japan consulting sector  |  AI disruption tracking  |  {datetime.now().strftime('%Y-%m-%d')}")

# Sidebar
st.sidebar.markdown("### PARAMETERS")
metric_choice = st.sidebar.selectbox(
    "VALUATION METRIC",
    ["P/E (株価収益率)", "P/S (株価売上高倍率)", "EV/EBITDA", "株価指数 (基準日=100)"],
)
metric_key = {
    "P/E (株価収益率)": "pe",
    "P/S (株価売上高倍率)": "ps",
    "EV/EBITDA": "ev_ebitda",
    "株価指数 (基準日=100)": "price_index",
}[metric_choice]

period = st.sidebar.selectbox("PERIOD", ["1y", "2y", "3y", "5y"], index=1)
show_forecast = st.sidebar.checkbox("Show forecast", value=True)
forecast_days = st.sidebar.slider("Forecast days", 30, 180, FORECAST_DAYS)

selected_categories = st.sidebar.multiselect(
    "CATEGORIES",
    ALL_CATEGORIES,
    default=ALL_CATEGORIES,
)

available_tickers = {
    t: m for t, m in TICKERS.items() if m["category"] in selected_categories
}
all_ticker_labels = [f"{m['name']} ({t})" for t, m in available_tickers.items()]

st.sidebar.markdown("---")
st.sidebar.markdown("### EXCLUDE")
excluded_labels = st.sidebar.multiselect(
    "Remove from view",
    all_ticker_labels,
    default=[],
)
excluded_tickers = set()
for label in excluded_labels:
    for t, m in available_tickers.items():
        if f"{m['name']} ({t})" == label:
            excluded_tickers.add(t)

active_tickers = {
    t: m for t, m in available_tickers.items() if t not in excluded_tickers
}

# ─────────────────────────────────────────────
# Main Chart
# ─────────────────────────────────────────────
progress_bar = st.progress(0, text="Fetching price data...")
# 全銘柄の株価を一括ダウンロード（APIコール1回）
all_ticker_list = list(active_tickers.keys())
bulk_data = fetch_all_history(all_ticker_list, period)
progress_bar.progress(20, text="Fetching fundamentals...")

fig = go.Figure()
fig.update_layout(**MCK_LAYOUT)
summary_rows = []
alerts = []
category_series = {cat: [] for cat in ALL_CATEGORIES}
total = len(active_tickers)

for i, (ticker, meta) in enumerate(active_tickers.items()):
    if i > 0:
        time.sleep(1)
    pct = 20 + int(70 * (i + 1) / total)
    progress_bar.progress(pct, text=f"Loading {meta['name']}... ({i+1}/{total})")
    hist, info = fetch_data_from_bulk(bulk_data, ticker)
    if hist is None or info is None:
        continue
        df = compute_valuation_series(hist, info)
        series = df[metric_key].dropna()
        if series.empty:
            continue

        cat = meta["category"]
        category_series[cat].append(series)

        # Individual — thin, muted
        fig.add_trace(go.Scatter(
            x=series.index, y=series.values,
            mode="lines",
            name=meta["name"],
            line=dict(color=meta["color"], width=1.2),
            opacity=0.35,
            legendgroup=cat,
            legendgrouptitle_text=cat,
            hovertemplate=f"{meta['name']}<br>%{{x|%Y-%m-%d}}<br>{metric_choice}: %{{y:.1f}}<extra></extra>",
        ))

        current_val = series.iloc[-1]
        max_val = series.max()
        min_val = series.min()
        pct_from_peak = ((current_val - max_val) / max_val) * 100

        summary_rows.append({
            "銘柄": meta["name"],
            "Ticker": ticker,
            "カテゴリ": cat,
            f"Current {metric_choice}": round(current_val, 2),
            "Period High": round(max_val, 2),
            "Period Low": round(min_val, 2),
            "% from Peak": round(pct_from_peak, 1),
        })

        if pct_from_peak > -10:
            alerts.append((meta["name"], pct_from_peak))

    # Category averages — bold, prominent
    for cat in ALL_CATEGORIES:
        if cat not in selected_categories or not category_series[cat]:
            continue

        avg_color = CATEGORY_AVG_COLORS[cat]
        combined = pd.concat(category_series[cat], axis=1)
        cat_mean = combined.mean(axis=1).dropna()
        if cat_mean.empty:
            continue

        fill_color = f"rgba({int(avg_color[1:3],16)},{int(avg_color[3:5],16)},{int(avg_color[5:7],16)},0.12)"

        # カテゴリ平均線（太線）
        fig.add_trace(go.Scatter(
            x=cat_mean.index, y=cat_mean.values,
            mode="lines",
            name=f"Avg: {cat}",
            line=dict(color=avg_color, width=3.5),
            opacity=1.0,
            legendgroup=cat,
            hovertemplate=f"Avg: {cat}<br>%{{x|%Y-%m-%d}}<br>{metric_choice}: %{{y:.1f}}<extra></extra>",
        ))

        # 予測延長（ボリンジャーバンド）
        if show_forecast:
            fdates, f_sma, f_upper, f_lower = forecast_bb(cat_mean, forecast_days)
            if fdates is not None:
                fig.add_trace(go.Scatter(
                    x=fdates, y=f_upper,
                    mode="lines", line=dict(width=0),
                    legendgroup=cat, showlegend=False, hoverinfo="skip",
                ))
                fig.add_trace(go.Scatter(
                    x=fdates, y=f_lower,
                    mode="lines", line=dict(width=0),
                    fill="tonexty", fillcolor=fill_color,
                    legendgroup=cat, showlegend=False, hoverinfo="skip",
                ))
                fig.add_trace(go.Scatter(
                    x=fdates, y=f_sma,
                    mode="lines",
                    name=f"Forecast: {cat}",
                    line=dict(color=avg_color, width=2.5, dash="dot"),
                    opacity=0.8,
                    legendgroup=cat, showlegend=False,
                    hovertemplate=f"Forecast: {cat}<br>%{{x|%Y-%m-%d}}<br>{metric_choice}: %{{y:.1f}}<extra></extra>",
                ))

    fig.update_layout(
        height=620,
        title=dict(text=f"{metric_choice}  —  Daily trend with category averages"),
        yaxis=dict(autorange=True, fixedrange=False, side="left"),
        legend=dict(
            orientation="v", y=1, x=1.02,
            groupclick="togglegroup",
        ),
        hovermode="x unified",
    )
    progress_bar.progress(100, text="Complete")
    progress_bar.empty()
    st.plotly_chart(fig, use_container_width=True, key="main_chart")

    st.markdown(
        f'<div style="color:{MCK_GREY}; font-size:0.72rem; line-height:1.6; margin-top:-0.5rem;">'
        f'* Analysis period: {period} &ensp;|&ensp;'
        f'Trend line: OLS linear regression over full period &ensp;|&ensp;'
        f'Forecast band: ±2σ (daily return vol × √t), expanding cone from last data point'
        f'</div>',
        unsafe_allow_html=True,
    )

