"""データ取得・キャッシュ・PER計算・トレンド予測（UI非依存）"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests
import yfinance as yf
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
# Universe
#   eps_source:
#     "yahoo_q" … Yahoo の四半期 Reported EPS を直近4Qで合算（TTM）
#     "yahoo_a" … Yahoo の年次 Diluted EPS（四半期データが無い銘柄用）
#     "irbank"  … IRBank の通期EPS（日本株）
# ─────────────────────────────────────────────
TICKERS = {
    # 米国コンサル
    "ACN":    {"name": "Accenture",              "category": "米国コンサル"},
    "IT":     {"name": "Gartner",                "category": "米国コンサル"},
    "BAH":    {"name": "Booz Allen Hamilton",    "category": "米国コンサル"},
    "KFY":    {"name": "Korn Ferry",             "category": "米国コンサル"},
    "FCN":    {"name": "FTI Consulting",         "category": "米国コンサル"},
    "EXPO":   {"name": "Exponent",               "category": "米国コンサル"},
    "HURN":   {"name": "Huron Consulting",       "category": "米国コンサル"},
    "ICFI":   {"name": "ICF International",      "category": "米国コンサル"},
    "CRAI":   {"name": "CRA International",      "category": "米国コンサル"},
    # グローバルITサービス
    "INFY":     {"name": "Infosys",              "category": "グローバルITサービス"},
    "CTSH":     {"name": "Cognizant",            "category": "グローバルITサービス"},
    "CAP.PA":   {"name": "Capgemini",            "category": "グローバルITサービス", "eps_source": "yahoo_a"},
    "WIT":      {"name": "Wipro",                "category": "グローバルITサービス"},
    "GIB-A.TO": {"name": "CGI",                  "category": "グローバルITサービス"},
    "EPAM":     {"name": "EPAM Systems",         "category": "グローバルITサービス"},
    "G":        {"name": "Genpact",              "category": "グローバルITサービス"},
    # 日本コンサル
    # 2026/03期は一過性の大幅減益（純利益153億円）でPERが飛ぶため、そのEPSが効いている期間を除外
    "4307.T": {"name": "野村総研(NRI)",           "category": "日本コンサル", "exclude_eps": ["2026-05-15"]},
    "6532.T": {"name": "ベイカレント",            "category": "日本コンサル"},
    "4722.T": {"name": "フューチャー",            "category": "日本コンサル"},
    "446A.T": {"name": "ノースサンド",            "category": "日本コンサル"},
    "9757.T": {"name": "船井総研HD",              "category": "日本コンサル"},
    "277A.T": {"name": "グロービング",            "category": "日本コンサル"},
    "6088.T": {"name": "シグマクシス",            "category": "日本コンサル"},
    "4792.T": {"name": "山田コンサル",            "category": "日本コンサル"},
    "3798.T": {"name": "ULSグループ",             "category": "日本コンサル"},
    "4310.T": {"name": "ドリームインキュベータ",   "category": "日本コンサル"},
    "9556.T": {"name": "INTLOOP",                "category": "日本コンサル"},
    "9168.T": {"name": "ライズコンサルティング",   "category": "日本コンサル"},
    "6560.T": {"name": "エル・ティー・エス",       "category": "日本コンサル"},
    # AI系
    "PLTR":   {"name": "Palantir",               "category": "AI系"},
    "AI":     {"name": "C3.ai",                  "category": "AI系"},
    "3993.T": {"name": "PKSHA Technology",       "category": "AI系"},
    "4259.T": {"name": "エクサウィザーズ",         "category": "AI系"},
    "5574.T": {"name": "ABEJA",                  "category": "AI系"},
    "4382.T": {"name": "HEROZ",                  "category": "AI系"},
    "5572.T": {"name": "Ridge-i",                "category": "AI系"},
}
for _t, _m in TICKERS.items():
    _m.setdefault("eps_source", "irbank" if _t.endswith(".T") else "yahoo_q")

ALL_CATEGORIES = ["米国コンサル", "グローバルITサービス", "日本コンサル", "AI系"]

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
PRICES_FILE = os.path.join(DATA_DIR, "prices.parquet")
FUND_FILE = os.path.join(DATA_DIR, "fundamentals.json")

HISTORY_YEARS = 5
FUND_MAX_AGE_DAYS = 7          # EPSは四半期更新なので週1で十分
JP_DISCLOSURE_LAG_DAYS = 45    # 決算期末→決算短信までの想定ラグ
ANNUAL_DISCLOSURE_LAG_DAYS = 60
UA = {"User-Agent": "Mozilla/5.0"}
FX_TICKERS = {"JPY": "JPYUSD=X", "EUR": "EURUSD=X", "CAD": "CADUSD=X"}


def _retry(fn, attempts=3, wait=3):
    for i in range(attempts):
        try:
            return fn()
        except Exception:
            if i == attempts - 1:
                raise
            time.sleep(wait * (i + 1))


# ─────────────────────────────────────────────
# Prices
# ─────────────────────────────────────────────
def _download_close(tickers, start):
    """終値（配当未調整・分割調整済み）をワイド形式で取得"""
    raw = _retry(lambda: yf.download(
        tickers, start=start, group_by="ticker", auto_adjust=False,
        progress=False, threads=True,
    ))
    if raw is None or raw.empty:
        return pd.DataFrame()
    out = {}
    for t in tickers:
        if isinstance(raw.columns, pd.MultiIndex):
            if t not in raw.columns.get_level_values(0):
                continue
            s = raw[t]["Close"]
        else:
            s = raw["Close"]
        s = s.dropna()
        if not s.empty:
            out[t] = s
    df = pd.DataFrame(out)
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df


def load_prices():
    if os.path.exists(PRICES_FILE):
        return pd.read_parquet(PRICES_FILE)
    return pd.DataFrame()


def update_prices(tickers, prices=None):
    """未取得銘柄は5年分、既存銘柄は最終日以降の差分のみ取得"""
    prices = load_prices() if prices is None else prices
    today = pd.Timestamp.now().normalize()
    full_start = (today - pd.DateOffset(years=HISTORY_YEARS)).strftime("%Y-%m-%d")

    missing = [t for t in tickers if t not in prices.columns]
    existing = [t for t in tickers if t in prices.columns]

    frames = [prices]
    if missing:
        frames.append(_download_close(missing, full_start))
    if existing:
        # 銘柄ごとの最終有効日のうち最も古い日から取り直す（部分欠損の自己修復）
        last_valid = min(prices[t].last_valid_index() or prices.index[0] for t in existing)
        if last_valid < today - pd.Timedelta(days=1):
            start = (last_valid - pd.Timedelta(days=3)).strftime("%Y-%m-%d")
            frames.append(_download_close(existing, start))

    frames = [f for f in frames if f is not None and not f.empty]
    if not frames:
        return prices
    combined = frames[0]
    for f in frames[1:]:
        combined = f.combine_first(combined)  # 新しい取得値を優先
    combined = combined.sort_index()
    combined = combined[combined.index >= pd.Timestamp(full_start)]
    os.makedirs(DATA_DIR, exist_ok=True)
    combined.to_parquet(PRICES_FILE)
    return combined


# ─────────────────────────────────────────────
# EPS
# ─────────────────────────────────────────────
def _parse_jp_number(s):
    s = s.replace(",", "").replace("+", "").replace("%", "").replace("*", "").strip()
    if s in ("", "-", "—"):
        return None
    for unit, mult in (("兆", 1e12), ("億", 1e8), ("百万", 1e6), ("千", 1e3)):
        if unit in s:
            return float(s.replace(unit, "")) * mult
    return float(s)


def fetch_irbank_eps(code):
    """IRBank通期業績から (実績EPS系列, 予想EPS) を返す。列はヘッダー名で特定"""
    r = requests.get(f"https://irbank.net/{code}/results", headers=UA, timeout=15)
    r.raise_for_status()
    tables = BeautifulSoup(r.text, "html.parser").find_all("table")
    if not tables:
        return [], None
    rows = [[c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
            for tr in tables[0].find_all("tr")]
    header = rows[0]
    if "EPS" not in header:
        return [], None
    ei = header.index("EPS")

    points, forward = [], None
    for cells in rows[1:]:
        if len(cells) <= ei or not cells[0][:4].isdigit():
            continue  # 末尾の繰り返しヘッダー行など
        try:
            eps = _parse_jp_number(cells[ei])
        except ValueError:
            continue
        label = cells[0]
        if "予" in label:
            forward = eps
            continue
        if eps is None:
            continue
        fy_end = pd.Timestamp(label[:7].replace("/", "-") + "-01") + pd.offsets.MonthEnd(0)
        points.append(((fy_end + pd.Timedelta(days=JP_DISCLOSURE_LAG_DAYS)).strftime("%Y-%m-%d"), eps))
    return points, forward


def fetch_yahoo_quarterly_eps(tk):
    """四半期Reported EPSから、各決算発表日時点のTTM EPS系列を作る"""
    ed = tk.get_earnings_dates(limit=40)
    if ed is None or ed.empty:
        return []
    rep = ed["Reported EPS"].dropna()
    rep.index = pd.to_datetime(rep.index).tz_localize(None).normalize()
    rep = rep[~rep.index.duplicated()].sort_index()
    points = []
    for i in range(3, len(rep)):
        window = rep.iloc[i - 3:i + 1]
        # 4四半期が約1年に収まっていない（欠損がある）場合はスキップ
        if (window.index[-1] - window.index[0]).days > 330:
            continue
        points.append((rep.index[i].strftime("%Y-%m-%d"), float(window.sum())))
    return points


def fetch_yahoo_annual_eps(tk):
    inc = tk.income_stmt
    if inc is None or inc.empty or "Diluted EPS" not in inc.index:
        return []
    s = inc.loc["Diluted EPS"].dropna().sort_index()
    return [((pd.Timestamp(d) + pd.Timedelta(days=ANNUAL_DISCLOSURE_LAG_DAYS)).strftime("%Y-%m-%d"), float(v))
            for d, v in s.items()]


def fetch_fundamentals(ticker):
    meta = TICKERS[ticker]
    tk = yf.Ticker(ticker)
    info = _retry(lambda: tk.info) or {}
    src = meta["eps_source"]
    if src == "irbank":
        points, forward = _retry(lambda: fetch_irbank_eps(ticker.replace(".T", "")))
    elif src == "yahoo_a":
        points, forward = _retry(lambda: fetch_yahoo_annual_eps(tk)), info.get("forwardEps")
    else:
        points, forward = _retry(lambda: fetch_yahoo_quarterly_eps(tk)), info.get("forwardEps")
    return {
        "currency": info.get("currency"),
        "market_cap": info.get("marketCap"),
        "eps_points": points,
        "forward_eps": forward,
        "eps_source": src,
    }


def load_fundamentals():
    if os.path.exists(FUND_FILE):
        with open(FUND_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"data": {}, "updated": {}, "fx": {}}


def _fetch_fx():
    fx = {"USD": 1.0}
    for cur, sym in FX_TICKERS.items():
        try:
            h = yf.Ticker(sym).history(period="5d")["Close"].dropna()
            if not h.empty:
                fx[cur] = float(h.iloc[-1])
        except Exception:
            pass
    return fx


def update_fundamentals(tickers, fund=None, force=False, on_progress=None):
    """古い（FUND_MAX_AGE_DAYS超）銘柄だけ再取得。失敗しても既存値は保持"""
    fund = load_fundamentals() if fund is None else fund
    fund.setdefault("data", {})
    fund.setdefault("updated", {})
    today = datetime.now().date()
    stale = [
        t for t in tickers
        if force or t not in fund["data"]
        or (today - datetime.strptime(fund["updated"].get(t, "2000-01-01"), "%Y-%m-%d").date()).days > FUND_MAX_AGE_DAYS
    ]
    failed = []
    for i, t in enumerate(stale):
        if on_progress:
            on_progress(i, len(stale), t)
        try:
            fund["data"][t] = fetch_fundamentals(t)
            fund["updated"][t] = today.strftime("%Y-%m-%d")
        except Exception:
            failed.append(t)
        time.sleep(0.8)  # Yahoo / IRBank のレート制限対策
    if stale:
        fx = _fetch_fx()
        if len(fx) > 1:
            fund["fx"] = fx
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(FUND_FILE, "w", encoding="utf-8") as f:
            json.dump(fund, f, ensure_ascii=False, indent=1)
    return fund, failed


# ─────────────────────────────────────────────
# Valuation
# ─────────────────────────────────────────────
def eps_series(points, index):
    """EPSの時点系列を日次インデックスへ as-of 展開（発表日以降に反映）"""
    if not points:
        return pd.Series(np.nan, index=index)
    s = pd.Series({pd.Timestamp(d): v for d, v in points}).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    return s.reindex(s.index.union(index)).ffill().reindex(index)


def per_series(price, points, exclude_eps=()):
    """実績PER。EPS<=0（赤字）の期間と、exclude_eps（反映日）のEPSが効いている期間はNaN"""
    price = price.dropna()
    eps = eps_series(points, price.index)
    per = price / eps
    per = per.where(eps > 0)
    if exclude_eps and points:
        dates = pd.Series({pd.Timestamp(d): pd.Timestamp(d) for d, _ in points}).sort_index()
        active = dates.reindex(dates.index.union(price.index)).ffill().reindex(price.index)
        per = per.where(~active.isin([pd.Timestamp(d) for d in exclude_eps]))
    return per


def usd_market_cap(f, fx):
    mc, cur = f.get("market_cap"), f.get("currency")
    if not mc or not cur or cur not in fx:
        return None
    return mc * fx[cur]


def category_aggregate(series_list, how="median"):
    """銘柄間の休場日ズレを前方補完で吸収してから集計"""
    if not series_list:
        return pd.Series(dtype=float)
    panel = pd.concat(series_list, axis=1).sort_index().ffill(limit=5)
    agg = panel.median(axis=1) if how == "median" else panel.mean(axis=1)
    return agg.dropna()


def forecast_trend(series, days, z=2.0):
    """対数PERの線形トレンドを延長し、日次対数変化σ×√t の±zσコーンを付ける"""
    s = series.dropna()
    s = s[s > 0]
    if len(s) < 60:
        return None
    y = np.log(s.values)
    slope = np.polyfit(np.arange(len(y)), y, 1)[0]
    sigma = np.diff(y).std(ddof=1)
    last_date = s.index[-1]
    future = pd.bdate_range(start=last_date + timedelta(days=1), end=last_date + timedelta(days=days))
    t = np.arange(len(future) + 1)
    center = s.iloc[-1] * np.exp(slope * t)
    band = np.exp(z * sigma * np.sqrt(t))
    dates = pd.DatetimeIndex([last_date]).append(future)
    return dates, center, center * band, center / band
