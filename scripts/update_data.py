"""data/ 以下のキャッシュ（株価・EPS）を最新化する。

    python scripts/update_data.py          # 古いものだけ更新
    python scripts/update_data.py --force  # EPSを全銘柄取り直す
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core  # noqa: E402

force = "--force" in sys.argv
tickers = list(core.TICKERS)

prices = core.update_prices(tickers)
print(f"prices: {prices.index.min().date()} → {prices.index.max().date()}, {prices.shape[1]} tickers")
missing = sorted(set(tickers) - set(prices.columns))
if missing:
    print("  price missing:", missing)

fund, failed = core.update_fundamentals(
    tickers, force=force,
    on_progress=lambda i, n, t: print(f"  fundamentals {i + 1}/{n}: {t}"),
)
if failed:
    print("  fundamentals failed:", failed)
for t in tickers:
    f = fund["data"].get(t, {})
    pts = f.get("eps_points") or []
    last = pts[-1] if pts else None
    print(f"{t:9} {f.get('eps_source'):8} n={len(pts):2} last={last} fwd={f.get('forward_eps')}")
print("fx:", fund.get("fx"))
