# Consulting Valuation Monitor

米国コンサル / グローバルITサービス / 日本コンサル / AI系 の実績PER推移を比較する Streamlit ダッシュボード。

```bash
pip install -r requirements.txt
streamlit run app.py
```

## データ
- `data/prices.parquet` … 終値（5年分）。起動時に差分のみ取得
- `data/fundamentals.json` … EPS履歴・予想EPS・時価総額・為替。週1回自動更新
- 手動更新: `python scripts/update_data.py`（`--force` でEPSを全銘柄取り直し）

## 銘柄の追加
`core.py` の `TICKERS` に1行追加するだけ。日本株（`.T`）は IRBank、それ以外は Yahoo の四半期EPSを自動で使う。
四半期EPSが無い銘柄は `"eps_source": "yahoo_a"`（年次EPS）を指定。
次回起動時にその銘柄だけ5年分を取得する。
