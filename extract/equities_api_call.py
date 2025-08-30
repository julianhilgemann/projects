# pipeline/fetch_equities.py
# Fetches German equities (daily) via yfinance
# Writes: data_raw/equities_de_daily.csv

import os
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    raise SystemExit("yfinance not installed. Run: pip install yfinance")

ROOT = os.path.dirname(os.path.dirname(__file__)) if "__file__" in globals() else "."
RAW  = os.path.join(ROOT, "data_raw")
os.makedirs(RAW, exist_ok=True)

# === Settings ===
EQ_START = "2010-01-01"
TICKERS  = ["SAP.DE", "SIE.DE", "ALV.DE", "BAS.DE", "BMW.DE"]

def main():
    print(f"→ Downloading equities via yfinance: {', '.join(TICKERS)} …")
    px = yf.download(TICKERS, start=EQ_START, progress=False, auto_adjust=True)
    if "Close" in px.columns:
        px = px["Close"]
    px = px.rename_axis("Date").reset_index()

    # long format (Date, Ticker, Close_EUR)
    px_long = (
        px.melt(id_vars="Date", var_name="Ticker", value_name="Close_EUR")
          .dropna()
          .sort_values(["Ticker", "Date"])
    )

    outfile = os.path.join(RAW, "equities_de_daily.csv")
    px_long.to_csv(outfile, index=False)
    print(f"  ✓ {outfile}  ({len(px_long)} rows, {px_long['Ticker'].nunique()} tickers)")

if __name__ == "__main__":
    pd.set_option("display.width", 140)
    pd.set_option("display.max_columns", 20)
    main()