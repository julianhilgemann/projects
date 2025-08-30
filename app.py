# Streamlit portfolio prototype (equal-weight, monthly rebalance)
# Reads: data_raw/equities_de_daily.csv  with columns: date, Ticker, Close_EUR

from __future__ import annotations
import math
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from pathlib import Path
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

# ---------- Settings ----------
DEFAULT_TICKERS = ["SAP.DE", "SIE.DE", "ALV.DE", "BAS.DE", "BMW.DE"]
TRADING_DAYS = 252

# ---------- Utils ----------
def norm_ppf(p: float) -> float:
    """Inverse CDF of standard normal (Acklam's rational approximation).
       No SciPy dependency; good to ~1e-6 on (0,1).
    """
    if not (0.0 < p < 1.0):
        raise ValueError("p must be in (0,1)")
    a = [-3.969683028665376e+01,  2.209460984245205e+02,
         -2.759285104469687e+02,  1.383577518672690e+02,
         -3.066479806614716e+01,  2.506628277459239e+00]
    b = [-5.447609879822406e+01,  1.615858368580409e+02,
         -1.556989798598866e+02,  6.680131188771972e+01,
         -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01,
         -2.400758277161838e+00, -2.549732539343734e+00,
          4.374664141464968e+00,  2.938163982698783e+00]
    d = [ 7.784695709041462e-03,  3.224671290700398e-01,
          2.445134137142996e+00,  3.754408661907416e+00]
    plow = 0.02425
    phigh = 1 - plow
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
               ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1)
    if phigh < p:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
                 ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1)
    q = p - 0.5
    r = q*q
    return (((((a[0]*r + a[1])*r + a[2])*r + a[3])*r + a[4])*r + a[5]) * q / \
           (((((b[0]*r + b[1])*r + b[2])*r + b[3])*r + b[4])*r + 1)

def month_key(d: pd.Series) -> pd.Series:
    return d.dt.to_period("M").dt.to_timestamp()

def max_drawdown(equity: pd.Series) -> float:
    roll_max = equity.cummax()
    return (equity / roll_max - 1.0).min()

def cagr(equity: pd.Series, trading_days=TRADING_DAYS) -> float:
    if equity.empty:
        return np.nan
    total_return = equity.iloc[-1] / equity.iloc[0] - 1.0
    years = len(equity) / trading_days
    return (1.0 + total_return) ** (1.0 / years) - 1.0 if years > 0 else np.nan

# ---------- Data loading / transforms (cached) ----------
@st.cache_data(show_spinner=False)
def load_prices(csv_path: Path, sig: Tuple[int, int]) -> pd.DataFrame:
    """Read CSV and normalize columns. 'sig' = (mtime, size) for cache invalidation."""
    df = pd.read_csv(csv_path)
    cols = {c.lower().strip(): c for c in df.columns}
    date_col = cols.get("date") or cols.get("dt")
    if not date_col:
        st.error("CSV must contain a 'date' or 'dt' column.")
        st.stop()
    if "ticker" not in [c.lower() for c in df.columns]:
        st.error("CSV must contain a 'Ticker' column.")
        st.stop()
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

@st.cache_data(show_spinner=False)
def compute_returns(df_prices: pd.DataFrame) -> pd.DataFrame:
    df = df_prices.sort_values(["ticker", "dt"]).copy()
    df["r"] = df.groupby("ticker")["price"].pct_change()
    return df.dropna(subset=["r"])

@st.cache_data(show_spinner=False)
def run_engine_cached(
    r_df: pd.DataFrame,
    tickers: Tuple[str, ...],
    start_cash: float,
    tc_bps: float,
    rf_annual: float,
    start_date: Optional[pd.Timestamp],
    end_date: Optional[pd.Timestamp],
    alpha: float,
):
    return portfolio_engine_equal_monthly(
        r_df, list(tickers), start_cash, tc_bps/10000.0, rf_annual, start_date, end_date, alpha
    )

# ---------- Engine ----------
def portfolio_engine_equal_monthly(
    r_df: pd.DataFrame,
    tickers: list[str],
    start_cash: float,
    tc_pct: float,
    rf_annual: float,
    start_date: Optional[pd.Timestamp],
    end_date: Optional[pd.Timestamp],
    alpha: float = 0.95,
):
    """Return: daily (DataFrame), summary (dict), wide_ret (DataFrame), turnover (Series by month)."""
    df = r_df[r_df["ticker"].isin([t.upper() for t in tickers])].copy()
    if start_date is not None:
        df = df[df["dt"] >= start_date]
    if end_date is not None:
        df = df[df["dt"] <= end_date]
    if df.empty:
        return pd.DataFrame(), {}, pd.DataFrame(), pd.Series(dtype=float)

    # Pivot to wide; require full basket each day to keep it simple
    wide = df.pivot(index="dt", columns="ticker", values="r").sort_index().dropna(how="any")
    tickers = list(wide.columns)

    mkey = month_key(wide.index.to_series())
    months = mkey.unique()

    w_equal = pd.Series(1.0 / len(tickers), index=tickers)

    # Monthly gross return per ticker: Π(1+r) - 1
    g_month = wide.groupby(mkey).apply(lambda g: (1.0 + g).prod() - 1.0).sort_index()

    # Turnover between drifted end-of-month weights and next month's equal target
    turnover = pd.Series(0.0, index=months)
    for i, m in enumerate(months):
        if i == 0:
            continue
        prev = months[i - 1]
        grow = 1.0 + g_month.loc[prev]
        w_end = (w_equal * grow)
        w_end = w_end / w_end.sum()
        turnover.iloc[i] = float((w_end - w_equal).abs().sum())

    # Daily portfolio return (weights = equal within month)
    r_port = (wide * w_equal.values).sum(axis=1)

    # Apply transaction cost on first trading day of each month (except first)
    cost_applied = pd.Series(0.0, index=r_port.index)
    for i, m in enumerate(months):
        day = r_port.index[mkey[r_port.index] == m][0]
        if i == 0:
            continue
        cost = tc_pct * turnover.iloc[i]
        cost_applied.loc[day] = cost
        r_port.loc[day] = r_port.loc[day] - cost

    equity = start_cash * (1.0 + r_port).cumprod()

    # Risk / summary
    ann_mu = r_port.mean() * TRADING_DAYS
    ann_sigma = r_port.std(ddof=1) * np.sqrt(TRADING_DAYS)
    sharpe = (ann_mu - rf_annual) / ann_sigma if ann_sigma > 0 else np.nan
    mdd = max_drawdown(equity)
    total_return = equity.iloc[-1] / equity.iloc[0] - 1.0
    cagr_val = cagr(equity, TRADING_DAYS)

    # VaR/ES (daily) at chosen alpha
    z = norm_ppf(alpha)
    mu_d, sd_d = r_port.mean(), r_port.std(ddof=1)
    var_norm = -(mu_d - z * sd_d)  # VaR reported as positive loss fraction
    losses = -r_port.dropna()
    var_hist = losses.quantile(alpha)
    es_hist = losses[losses >= var_hist].mean()

    daily = pd.DataFrame({
        "dt": r_port.index,
        "r_port": r_port.values,
        "equity": equity.values,
        "m": mkey[r_port.index].values,
        "cost_applied": cost_applied.values
    }).set_index("dt")

    summary = {
        "Final Equity": float(equity.iloc[-1]),
        "Total Return": float(total_return),
        "CAGR": float(cagr_val),
        "Ann. Vol": float(ann_sigma),
        "Ann. Sharpe": float(sharpe),
        "Max Drawdown": float(mdd),
        "VaR (norm, daily)": float(var_norm),
        "VaR (hist, daily)": float(var_hist),
        "ES (hist, daily)": float(es_hist),
        "Turnover (avg/month)": float(turnover.iloc[1:].mean()) if len(turnover) > 1 else 0.0
    }

    return daily, summary, wide, turnover

def try_garch(portfolio_returns: pd.Series):
    try:
        from arch import arch_model
    except Exception as e:
        return None, f"arch not installed. Run: pip install arch  (error: {e})"
    r = portfolio_returns.dropna() * 100.0
    if len(r) < 300:
        return None, "Not enough data for GARCH (need ~300+ observations)."
    am = arch_model(r, mean="Constant", vol="GARCH", p=1, q=1, dist="normal")
    res = am.fit(disp="off")
    cond_vol = res.conditional_volatility / 100.0
    return cond_vol, None

def time_axis_with_rs(fig):
    fig.update_layout(
        margin=dict(l=10, r=10, t=30, b=10),
        height=360,
        xaxis=dict(
            rangeslider=dict(visible=True),
            rangeselector=dict(
                buttons=[
                    dict(count=1, step="month", stepmode="backward", label="1M"),
                    dict(count=3, step="month", stepmode="backward", label="3M"),
                    dict(count=1, step="year",  stepmode="backward", label="1Y"),
                    dict(step="all", label="All"),
                ]
            ),
            type="date",
        ),
        hovermode="x unified",
    )
    return fig

# ---------- UI ----------
st.set_page_config(page_title="Portfolio Prototype", layout="wide")
st.title("Portfolio Prototype — Equal Weight, Monthly Rebalance")

root = Path(__file__).resolve().parent
csv_path = (root / "data_raw" / "equities_de_daily.csv").resolve()
sig = (int(csv_path.stat().st_mtime), int(csv_path.stat().st_size))
st.caption(f"Data source: {csv_path}")

df_prices = load_prices(csv_path, sig)
all_tickers = sorted(df_prices["ticker"].unique())

# Put controls in a FORM (recompute on button click)
with st.sidebar.form("settings"):
    st.header("Settings")
    sel_tickers = st.multiselect("Tickers", options=all_tickers, default=DEFAULT_TICKERS)
    start_cash = st.number_input("Starting capital (€)", min_value=1000.0, value=100000.0, step=1000.0)
    tc_bps = st.number_input("Rebalance transaction cost (bps of notional traded)", min_value=0.0, value=10.0, step=5.0)
    rf_annual = st.number_input("Risk-free (annual, %)", min_value=0.0, value=2.0, step=0.25) / 100.0
    alpha = st.slider("VaR/ES confidence", 0.80, 0.99, 0.95)
    min_dt, max_dt = df_prices["dt"].min(), df_prices["dt"].max()
    dr = st.date_input("Date range", (min_dt.date(), max_dt.date()))
    want_garch = st.checkbox("Fit GARCH(1,1) (if 'arch' installed)")
    submitted = st.form_submit_button("Run / Update")

# Default run on first load
if not sel_tickers:
    st.stop()
start_date = pd.to_datetime(dr[0]) if isinstance(dr, tuple) else None
end_date   = pd.to_datetime(dr[1]) if isinstance(dr, tuple) else None

# Cached computations
r_df = compute_returns(df_prices)
daily, summary, wide_ret, turnover = run_engine_cached(
    r_df, tuple(sel_tickers), start_cash, tc_bps, rf_annual, start_date, end_date, alpha
)

if daily.empty:
    st.warning("No data for the selection.")
    st.stop()

# ---------- KPI “cards” ----------
st.markdown("""
<style>
div[data-testid="stMetric"] { background: rgba(255,255,255,0.03); border-radius: 12px; padding: 12px; }
div[data-testid="stMetric"] > label { font-size: 0.9rem; }
div[data-testid="stMetricValue"] { font-size: 1.6rem; }
</style>
""", unsafe_allow_html=True)

row1 = st.columns(5)
row1[0].metric("Final Equity", f"€{summary['Final Equity']:,.0f}")
row1[1].metric("Total Return", f"{summary['Total Return']*100:,.2f}%")
row1[2].metric("CAGR", f"{summary['CAGR']*100:,.2f}%")
row1[3].metric("Ann. Vol", f"{summary['Ann. Vol']*100:,.2f}%")
row1[4].metric("Sharpe (ann.)", f"{summary['Ann. Sharpe']:.2f}")

row2 = st.columns(3)
row2[0].metric("Max Drawdown", f"{summary['Max Drawdown']*100:,.2f}%")
row2[1].metric(f"VaR (norm, {int(alpha*100)}%, daily)", f"{summary['VaR (norm, daily)']*100:,.2f}%")
row2[2].metric(f"ES (hist, {int(alpha*100)}%, daily)", f"{summary['ES (hist, daily)']*100:,.2f}%")

# ---------- Charts (Plotly with zoom/range slider) ----------
st.subheader("Equity Curve")
fig_equity = go.Figure()
fig_equity.add_trace(go.Scatter(x=daily.index, y=daily["equity"], mode="lines", name="Equity"))
st.plotly_chart(time_axis_with_rs(fig_equity), use_container_width=True, config={"displaylogo": False})

st.subheader("Daily Return (with monthly cost hits)")
fig_ret = px.line(daily.reset_index(), x="dt", y="r_port")
fig_ret.update_yaxes(tickformat=".2%")
st.plotly_chart(time_axis_with_rs(fig_ret), use_container_width=True, config={"displaylogo": False})

st.subheader("Monthly Turnover (estimate)")
turn_df = turnover.rename("turnover").to_frame()
turn_df.index = pd.to_datetime(turn_df.index)
fig_turn = px.bar(turn_df.reset_index().rename(columns={"index": "month"}), x="month", y="turnover")
fig_turn.update_yaxes(tickformat=".1%")
st.plotly_chart(time_axis_with_rs(fig_turn), use_container_width=True, config={"displaylogo": False})

# Optional GARCH
if want_garch:
    cond_vol, garch_msg = try_garch(daily["r_port"])
    if cond_vol is None:
        st.info(garch_msg)
    else:
        st.subheader("GARCH(1,1) Conditional Volatility (daily)")
        fig_g = px.line(x=cond_vol.index, y=cond_vol.values, labels={"x":"dt","y":"cond_vol"})
        fig_g.update_yaxes(tickformat=".2%")
        st.plotly_chart(time_axis_with_rs(fig_g), use_container_width=True, config={"displaylogo": False})

# Data preview
with st.expander("Show sample data"):
    st.dataframe(daily.reset_index().tail(10), use_container_width=True)

st.caption(
    "Equal-weight rebalanced monthly. Transaction cost applied on the first trading day of each month "
    "based on turnover between drifted end-of-month weights and equal target. "
    "VaR/ES are based on daily returns; Sharpe uses annualized mean/vol and the provided risk-free rate."
)