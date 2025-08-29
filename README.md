# 🔧 DE Macro & Portfolio One-Pager (WIP)

**TL;DR:** The old dashboards in my GitHub are **spare parts**.  
This is the **main project** I’m building now: a clean, finance-credible, single-page **Portfolio Management Dashboard** with **German rates, yield curve, 5 equities, and risk** — designed for hiring signal in BI/Finance (🇨🇭/🇩🇪 focus).

> **Status:** Work in progress. The README tells you exactly what’s coming and how it’s structured.

---

## Why this exists
I’m consolidating my previous experiments (synthetic sales UI, mini company FP&A, time-series lab) into **one flagship**: a dense, well-designed **Power BI one-pager** backed by a tiny, reproducible pipeline.

---

## What the dashboard will show (one page)
- **KPI strip:** YTD, CAGR, Max Drawdown, Vol(60D), Sharpe(60D), VaR/ES(95%).
- **Portfolio path:** equity curve + drawdown ribbon.
- **Rate environment:** **Bundesbank policy rate (monthly)** forward-filled to daily.
- **German yield curve:** a few tenors (e.g., 3M / 2Y / 10Y) daily.
- **5 German equities:** daily close (EUR), **equal-weight, monthly rebalance**.
- **Risk panel:** rolling Sharpe, return histogram, current target weights.

---

## Scope (locked, so it ships)
- **Compute** core metrics in **Python** → export CSV.
- **DuckDB** to assemble tidy tables → CSVs for Power BI.
- **Power BI** single page with a consistent **dark theme**.
- No dbt / APIs in v1 (may add later in a separate branch).

---

## Data contracts (planned CSVs)

`data_raw/`
- `cb_rate_monthly.csv` → `DateMonth (YYYY-MM-01), PolicyRate_pct`
- `de_yields_daily.csv` → `Date, TenorY (0.25|2|10), Yield_pct`
- `equities_de_daily.csv` → `Date, Ticker, Close_EUR` (5 large DE names)

`data_out/` (generated)
- `portfolio_daily.csv` → `Date, PortValue, PortRet, Drawdown, Vol60D, Sharpe60D, VaR95_252, ES95_252, W_[Asset]*`
- `rate_daily.csv`      → `Date, PolicyRate_pct` (forward-filled)
- `yields_long.csv`     → `Date, TenorY, Yield_pct`
- `equities_returns.csv`→ `Date, Ticker, Return`

---

## Repo layout (planned)
```yaml
portfolio-onepager/
├─ data_raw/
├─ data_out/ # generated
├─ pipeline/
│ ├─ build_portfolio.py # Python: returns, rebal, risk, exports
│ └─ wrangle_duckdb.sql # DuckDB: assemble tidy outputs
├─ powerbi/
│ ├─ PortfolioOnePager.pbix # single page
│ └─ theme_dark.json
└─ docs/
├─ README.md # this file
└─ screenshots/ # GIFs once the page is ready
```