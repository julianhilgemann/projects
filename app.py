# Streamlit portfolio prototype (equal-weight, monthly rebalance)
# Reads: data_raw/equities_de_daily.csv  with columns: date, Ticker, Close_EUR

import numpy as np
import pandas as pd
from pathlib import Path
import streamlit as st
from typing import Optional
import plotly.graph_objects as go
import plotly.express as px


# ---------- Settings ----------
DEFAULT_TICKERS = ["SAP.DE", "SIE.DE", "ALV.DE", "BAS.DE", "BMW.DE"]
TRADING_DAYS = 252

# ---------- Helpers ----------
@st.cache_data
def load_prices(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        st.error(f"CSV not found: {csv_path}")
        st.stop()
    df = pd.read_csv(csv_path)
    # Normalize column names
    cols = {c.lower().strip(): c for c in df.columns}
    # Prefer 'date' from raw CSV; but accept 'dt' if already transformed
    if "date" in cols:
        date_col = cols["date"]
    elif "dt" in cols:
        date_col = cols["dt"]
    else:
        st.error("CSV must contain a 'date' or 'dt' column.")
        st.stop()
    if "ticker" not in [c.lower() for c in df.columns]:
        st.error("CSV must contain a 'Ticker' column.")
        st.stop()
    # Price column guess
    price_col = None
    for guess in ["Close_EUR", "close_eur", "close", "adj_close", "Adj Close"]:
        if guess in df.columns:
            price_col = guess
            break
    if price_col is None:
        st.error("Could not find a price column (e.g., Close_EUR).")
        st.stop()

    df = df.rename(columns={date_col: "dt", "Ticker": "ticker", price_col: "price"})
    df["dt"] = pd.to_datetime(df["dt"])
    df["ticker"] = df["ticker"].str.upper()
    df = df.sort_values(["ticker", "dt"]).dropna(subset=["price"]).reset_index(drop=True)
    return df[["dt", "ticker", "price"]]

def daily_returns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["ticker", "dt"]).copy()
    df["r"] = df.groupby("ticker")["price"].pct_change()
    return df.dropna(subset=["r"])

def month_key(d: pd.Series) -> pd.Series:
    # First calendar day of the month (as Timestamp)
    return d.dt.to_period("M").dt.to_timestamp()

def max_drawdown(equity: pd.Series) -> float:
    roll_max = equity.cummax()
    drawdown = equity / roll_max - 1.0
    return drawdown.min()

def cagr(equity: pd.Series, trading_days=TRADING_DAYS) -> float:
    if equity.empty:
        return np.nan
    total_return = equity.iloc[-1] / equity.iloc[0] - 1.0
    years = len(equity) / trading_days
    return (1.0 + total_return) ** (1.0 / years) - 1.0 if years > 0 else np.nan

def portfolio_engine_equal_monthly(
    r_df: pd.DataFrame,
    tickers: list[str],
    start_cash: float,
    tc_pct: float,
    rf_annual: float,
    start_date: Optional[pd.Timestamp],   # <-- was pd.Timestamp | None
    end_date: Optional[pd.Timestamp],     # <-- was pd.Timestamp | None
):
    """Returns daily portfolio DataFrame with columns:
       dt, r_port, equity, m (month), turnover_on_rebalance, cost_applied, w_equal
    """
    df = r_df[r_df["ticker"].isin([t.upper() for t in tickers])].copy()
    if start_date is not None:
        df = df[df["dt"] >= start_date]
    if end_date is not None:
        df = df[df["dt"] <= end_date]
    if df.empty:
        return pd.DataFrame()

    # Pivot daily returns to wide (drop rows with any NaN to keep aligned basket)
    wide = df.pivot(index="dt", columns="ticker", values="r").sort_index()
    wide = wide.dropna(how="any")  # require all tickers present for simplicity
    tickers = list(wide.columns)

    # Month key per row, and first business day per month
    mkey = month_key(wide.index.to_series())
    months = mkey.unique()
    first_days = mkey.groupby(mkey).transform("min")
    # Equal weights each month across the available tickers
    w_equal = pd.Series(1.0 / len(tickers), index=tickers)

    # Compute monthly drifted end-of-month weights to estimate turnover
    # Monthly gross return per ticker: Π(1+r) - 1 within each month
    month_groups = wide.groupby(mkey)
    g_month = month_groups.apply(lambda g: (1.0 + g).prod() - 1.0)  # DataFrame: index=(month), cols=tickers
    g_month = g_month.sort_index()

    # Calculate turnover between months from drifted weights to equal weights
    # w_end_prev_i ∝ w_equal_i * (1 + R_i_prev_m), normalized
    turnover = pd.Series(0.0, index=months)
    prev_w_end = None
    for i, m in enumerate(months):
        if i == 0:
            prev_w_end = w_equal.copy()
            turnover.iloc[i] = 0.0
            continue
        prev = months[i - 1]
        grow = 1.0 + g_month.loc[prev]
        w_end = (w_equal * grow)
        w_end = w_end / w_end.sum()
        # target next month is equal again
        turnover.iloc[i] = float((w_end - w_equal).abs().sum())
        prev_w_end = w_end

    # Daily portfolio returns: within each month, weights = equal
    r_port = (wide * w_equal.values).sum(axis=1)

    # Apply transaction cost on first trading day of each month (except first)
    cost_applied = pd.Series(0.0, index=r_port.index)
    for i, m in enumerate(months):
        day = r_port.index[mkey[r_port.index] == m][0]  # first trading day in this month
        if i == 0:
            continue
        cost = tc_pct * turnover.iloc[i]
        cost_applied.loc[day] = cost
        r_port.loc[day] = r_port.loc[day] - cost  # subtract as a one-off hit

    # Equity curve
    equity = start_cash * (1.0 + r_port).cumprod()

    # Risk / summary
    ann_mu = r_port.mean() * TRADING_DAYS
    ann_sigma = r_port.std(ddof=1) * np.sqrt(TRADING_DAYS)
    sharpe = (ann_mu - rf_annual) / ann_sigma if ann_sigma > 0 else np.nan
    mdd = max_drawdown(equity)
    total_return = equity.iloc[-1] / equity.iloc[0] - 1.0
    cagr_val = cagr(equity, TRADING_DAYS)

    # VaR / ES (daily, 95%)
    alpha = 0.95
    z = 1.6448536269514722  # N^{-1}(0.95)
    mu_d, sd_d = r_port.mean(), r_port.std(ddof=1)
    var_norm = -(mu_d - z * sd_d)          # parametric VaR (loss as positive number)
    # historical VaR: 95% quantile of losses
    losses = -r_port.dropna()
    var_hist = losses.quantile(alpha)
    es_hist = losses[losses >= var_hist].mean()  # ES at alpha

    daily = pd.DataFrame({
        "dt": r_port.index,
        "r_port": r_port.values,
        "equity": equity.values,
        "m": mkey[r_port.index].values,
        "cost_applied": cost_applied.values
    }).set_index("dt")

    summary = {
        "Final Equity": equity.iloc[-1],
        "Total Return": total_return,
        "CAGR": cagr_val,
        "Ann. Vol": ann_sigma,
        "Ann. Sharpe": sharpe,
        "Max Drawdown": mdd,
        "VaR (norm, daily, 95%)": var_norm,
        "VaR (hist, daily, 95%)": var_hist,
        "ES (hist, daily, 95%)": es_hist,
        "Turnover (avg/month)": float(turnover.iloc[1:].mean()) if len(turnover) > 1 else 0.0
    }

    return daily, summary, wide, turnover

def try_garch(portfolio_returns: pd.Series):
    try:
        from arch import arch_model
    except Exception as e:
        return None, f"arch not installed. Run: pip install arch  (error: {e})"
    # Fit GARCH(1,1) on daily returns (as %)
    r = portfolio_returns.dropna() * 100.0
    if len(r) < 300:
        return None, "Not enough data for GARCH (need ~300+ observations)."
    am = arch_model(r, mean="Constant", vol="GARCH", p=1, q=1, dist="normal")
    res = am.fit(disp="off")
    cond_vol = res.conditional_volatility / 100.0  # back to fraction
    return cond_vol, None

# ---------- UI ----------
st.set_page_config(page_title="Portfolio Prototype", layout="wide")
st.title("Portfolio Prototype — Equal Weight, Monthly Rebalance")

root = Path(__file__).resolve().parent
# If you place this app in repo root, csv is at data_raw/...
csv_path = (root / "data_raw" / "equities_de_daily.csv").resolve()
st.caption(f"Data source: {csv_path}")

df_prices = load_prices(csv_path)

# Controls
with st.sidebar:
    st.header("Settings")
    sel_tickers = st.multiselect("Tickers", options=sorted(df_prices["ticker"].unique()),
                                 default=DEFAULT_TICKERS)
    if len(sel_tickers) == 0:
        st.stop()
    start_cash = st.number_input("Starting capital (€)", min_value=1000.0, value=10000.0, step=500.0)
    tc_bps = st.number_input("Rebalance transaction cost (bps of notional traded)",
                             min_value=0.0, value=10.0, step=5.0)
    rf_annual = st.number_input("Risk-free (annual, %)", min_value=0.0, value=2.0, step=0.25) / 100.0
    alpha = st.slider("VaR/ES confidence", 0.80, 0.99, 0.95)
    # date range
    min_dt, max_dt = df_prices["dt"].min(), df_prices["dt"].max()
    dr = st.date_input("Date range", (min_dt.date(), max_dt.date()))
    if isinstance(dr, tuple):
        start_date = pd.to_datetime(dr[0])
        end_date = pd.to_datetime(dr[1])
    else:
        start_date, end_date = None, None
    want_garch = st.checkbox("Fit GARCH(1,1) (if 'arch' installed)")

# Compute
df_r = daily_returns(df_prices)
daily, summary, wide_ret, turnover = portfolio_engine_equal_monthly(
    df_r, sel_tickers, start_cash, tc_pct=tc_bps/10000.0,
    rf_annual=rf_annual, start_date=start_date, end_date=end_date
)

if daily.empty:
    st.warning("No data for the selection.")
    st.stop()

# KPIs
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Final Equity", f"€{summary['Final Equity']:,.0f}")
k2.metric("Total Return", f"{summary['Total Return']*100:,.2f}%")
k3.metric("CAGR", f"{summary['CAGR']*100:,.2f}%")
k4.metric("Ann. Vol", f"{summary['Ann. Vol']*100:,.2f}%")
k5.metric("Sharpe (ann.)", f"{summary['Ann. Sharpe']:.2f}")

k6, k7, k8 = st.columns(3)
k6.metric("Max Drawdown", f"{summary['Max Drawdown']*100:,.2f}%")
k7.metric(f"VaR (norm, {int(alpha*100)}%, daily)", f"{summary['VaR (norm, daily, 95%)']*100:,.2f}%")
k8.metric(f"ES (hist, {int(alpha*100)}%, daily)", f"{summary['ES (hist, daily, 95%)']*100:,.2f}%")

# Charts
st.subheader("Equity Curve")
st.line_chart(daily["equity"])

st.subheader("Daily Return (with monthly cost hits)")
st.line_chart(daily["r_port"])

st.subheader("Monthly Turnover (estimate)")
turn_df = turnover.rename("turnover").to_frame()
turn_df.index.name = "month"
st.bar_chart(turn_df)

# Optional GARCH
if want_garch:
    cond_vol, garch_msg = try_garch(daily["r_port"])
    if cond_vol is None:
        st.info(garch_msg)
    else:
        st.subheader("GARCH(1,1) Conditional Volatility (daily)")
        st.line_chart(cond_vol)

# Data preview
with st.expander("Show sample data"):
    st.dataframe(daily.reset_index().tail(10), use_container_width=True)

st.caption("Notes: Equal-weight rebalanced monthly. Transaction cost applied on first trading day of each month "
           "based on turnover between drifted end-of-month weights and equal target. "
           "VaR/ES shown on daily returns; Sharpe uses annualized mean/vol and the provided risk-free rate.")