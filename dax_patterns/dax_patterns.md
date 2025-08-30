Here’s a tidy **markdown file** you can drop into your repo as `docs/dax_patterns.md`.

---

# DAX Patterns — Portfolio One-Pager

Practical snippets for a single-page **portfolio & rates** dashboard. Designed to work with:

* **Fact\_PortfolioDaily** (from `portfolio_daily.csv` or `portfolio_with_macro.csv`)
  Columns: `Date`, `PortValue`, `PortRet`, `Drawdown`, `Vol60D`, `Sharpe60D`, `VaR95_1d`, `ES95_1d`, `W_<Ticker>…`
* **Fact\_RateDaily** (from `rate_daily.csv`)
  Columns: `Date`, `PolicyRate_pct`
* **Fact\_Yields** (monthly or daily)
  Columns: `Date`, `Yield_<Tenor>_pct`
* **Dim\_Date** (relationship on `Date`)

> Tip: Keep portfolio risk heavy-lifting in Python; use DAX for light rollups, cards, and interactivity.

---

## 0) Setup & helpers

```DAX
-- Calendar (business days not required for visuals)
Dim_Date = CALENDAR ( DATE(2010,1,1), TODAY() )

-- Relationship: Dim_Date[Date] -> each Fact[*][Date]

-- Safe divide (use everywhere)
[DIVIDE] = 
VAR Num = SELECTEDVALUE ( 'Helper'[Num] )  -- not used directly; pattern only
VAR Den = SELECTEDVALUE ( 'Helper'[Den] )
RETURN DIVIDE ( Num, Den, BLANK() )
```

---

## 1) Basics (from facts)

```DAX
[Port Value]   = MAX ( Fact_PortfolioDaily[PortValue] )
[Daily Return] = AVERAGE ( Fact_PortfolioDaily[PortRet] )

-- If you prefer to reference precomputed columns as measures:
[Drawdown]     = AVERAGE ( Fact_PortfolioDaily[Drawdown] )
[Vol 60D]      = AVERAGE ( Fact_PortfolioDaily[Vol60D] )
[Sharpe 60D]   = AVERAGE ( Fact_PortfolioDaily[Sharpe60D] )
[VaR 95 (1d)]  = AVERAGE ( Fact_PortfolioDaily[VaR95_1d] )   -- usually negative
[ES 95 (1d)]   = AVERAGE ( Fact_PortfolioDaily[ES95_1d] )
```

---

## 2) Period anchors

```DAX
-- Start of current selection (first visible date)
[Start Date Selected] =
MINX ( ALLSELECTED ( 'Dim_Date'[Date] ), 'Dim_Date'[Date] )

-- End of current selection (last visible date)
[End Date Selected] =
MAX ( 'Dim_Date'[Date] )
```

---

## 3) YTD, Period Return, and CAGR

> Use **PortValue** (index) for stability. If you only have returns, see §4 for a pure-returns variant.

```DAX
-- Value at start of selection
[Start Value] =
VAR d0 = [Start Date Selected]
RETURN
    CALCULATE ( [Port Value],
        FILTER ( ALLSELECTED ( 'Dim_Date' ), 'Dim_Date'[Date] = d0 )
    )

-- Simple period return within current selection
[Return (Selected)] =
VAR v0 = [Start Value]
RETURN IF ( NOT ISBLANK ( v0 ),
            DIVIDE ( [Port Value] - v0, v0 ) )

-- YTD return (calendar year)
[YTD] =
VAR v0 =
    CALCULATE ( [Port Value],
        FILTER ( ALLSELECTED ( 'Dim_Date' ),
                 'Dim_Date'[Date] = STARTOFYEAR ( 'Dim_Date'[Date] ) ) )
RETURN IF ( NOT ISBLANK ( v0 ),
            DIVIDE ( [Port Value] - v0, v0 ) )

-- CAGR over the selected window
[CAGR] =
VAR d0    = [Start Date Selected]
VAR d1    = [End Date Selected]
VAR years = DIVIDE ( DATEDIFF ( d0, d1, DAY ), 365.0 )
VAR v0    = [Start Value]
VAR v1    = [Port Value]
RETURN IF ( years > 0 && NOT ( ISBLANK ( v0 ) || ISBLANK ( v1 ) ),
            POWER ( DIVIDE ( v1, v0 ), 1 / years ) - 1 )
```

---

## 4) Rolling windows (on-the-fly in DAX)

> Fine for small models. For big ones, precompute in Python.

```DAX
-- Rolling volatility (N business days)
[Rolling Vol N] =
VAR N = 60
RETURN
    STDEVX.P (
        DATESINPERIOD ( 'Dim_Date'[Date], MAX ( 'Dim_Date'[Date] ), -N, DAY ),
        [Daily Return]
    ) * SQRT ( 252 )

-- Rolling mean return (N)
[Rolling Mean N] =
VAR N = 60
RETURN
    AVERAGEX (
        DATESINPERIOD ( 'Dim_Date'[Date], MAX ( 'Dim_Date'[Date] ), -N, DAY ),
        [Daily Return]
    )

-- Rolling Sharpe (N) using Policy Rate as RF (approx daily = Policy/100/252)
[Rolling Sharpe N] =
VAR N    = 60
VAR rf_d =
    AVERAGEX (
        DATESINPERIOD ( 'Dim_Date'[Date], MAX ( 'Dim_Date'[Date] ), -N, DAY ),
        AVERAGE ( Fact_RateDaily[PolicyRate_pct] ) / 100 / 252
    )
VAR mu   =
    AVERAGEX (
        DATESINPERIOD ( 'Dim_Date'[Date], MAX ( 'Dim_Date'[Date] ), -N, DAY ),
        [Daily Return] - rf_d
    )
VAR vol  = [Rolling Vol N]
RETURN DIVIDE ( mu, vol )
```

---

## 5) Max drawdown (from PortValue)

```DAX
-- Peak value up to the current date (within selection)
[Peak To Date] =
MAXX (
    FILTER ( ALLSELECTED ( 'Dim_Date'[Date] ),
             'Dim_Date'[Date] <= MAX ( 'Dim_Date'[Date] ) ),
    [Port Value]
)

-- Drawdown today
[Drawdown (from Value)] =
DIVIDE ( [Port Value] - [Peak To Date], [Peak To Date] )

-- Max drawdown over the selection (most negative)
[Max Drawdown (Sel)] =
MINX ( ALLSELECTED ( 'Dim_Date'[Date] ), [Drawdown (from Value)] )
```

---

## 6) VaR & ES (95%) in DAX (rolling)

> If you didn’t precompute in Python, you can estimate with percentiles over a window.

```DAX
-- Rolling VaR 95% (1-day) over 252 days
[VaR95 (1d, 252D)] =
VAR T = DATESINPERIOD ( 'Dim_Date'[Date], MAX('Dim_Date'[Date]), -252, DAY )
RETURN
    PERCENTILEX.INC ( T, [Daily Return], 0.05 )

-- Rolling Expected Shortfall 95% (1-day) over 252 days
[ES95 (1d, 252D)] =
VAR T = DATESINPERIOD ( 'Dim_Date'[Date], MAX('Dim_Date'[Date]), -252, DAY )
VAR R = ADDCOLUMNS ( T, "r", [Daily Return] )
VAR thr = PERCENTILEX.INC ( R, [r], 0.05 )
RETURN
    AVERAGEX ( FILTER ( R, [r] <= thr ), [r] )
```

---

## 7) Rate & yield snippets

```DAX
-- Latest policy rate in context (last non-blank)
[Policy Rate (Last, %)] =
LASTNONBLANKVALUE ( 'Dim_Date'[Date], AVERAGE ( Fact_RateDaily[PolicyRate_pct] ) )

-- “As of” helper for subtitles/cards
[As Of Date] = MAX ( 'Dim_Date'[Date] )

-- Example: slope 10Y - 2Y (if both exist in Fact_Yields)
[Yield Slope (10y-2y, bp)] =
VAR y10 = AVERAGE ( Fact_Yields[Yield_10y_pct] )
VAR y02 = AVERAGE ( Fact_Yields[Yield_2y_pct] )
RETURN ( y10 - y02 ) * 100   -- basis points
```

---

## 8) YOY / Period-over-period deltas

```DAX
-- YoY return (using PortValue)
[Return YoY] =
VAR v_now =
    CALCULATE ( [Port Value],
        DATESINPERIOD ( 'Dim_Date'[Date], MAX('Dim_Date'[Date]), 0, DAY ) )
VAR v_ly =
    CALCULATE ( [Port Value],
        DATEADD ( 'Dim_Date'[Date], -1, YEAR ) )
RETURN
    IF ( NOT ( ISBLANK ( v_now ) || ISBLANK ( v_ly ) ),
         DIVIDE ( v_now - v_ly, v_ly ) )

-- MoM % change of policy rate (pct points)
[Policy Rate Δ MoM (pp)] =
VAR now = [Policy Rate (Last, %)]
VAR prev =
    CALCULATE ( [Policy Rate (Last, %)], DATEADD ( 'Dim_Date'[Date], -1, MONTH ) )
RETURN now - prev
```

---

## 9) Indicators & alerts (for tooltips/cards)

```DAX
-- ASCII trend indicator for Sharpe (↑/↓/•)
[Sharpe Trend Icon] =
VAR now  = [Sharpe 60D]
VAR prev =
    CALCULATE ( [Sharpe 60D], DATEADD ( 'Dim_Date'[Date], -5, DAY ) )
RETURN
    IF ( ISBLANK(now) || ISBLANK(prev), "•",
        IF ( now > prev + 0.05, "▲",
             IF ( now < prev - 0.05, "▼", "•" )
        )
    )

-- Simple alert banner
[Alert Banner] =
VAR dd = [Max Drawdown (Sel)]
VAR vr = [VaR95 (1d, 252D)]
RETURN
CONCATENATEX (
    {
      IF ( dd < -0.15, "⚠︎ Drawdown > 15%", BLANK() ),
      IF ( vr < -0.02, "⚠︎ 1-day VaR worse than -2%", BLANK() )
    },
    [Value], "   •   "
)
```

---

## 10) Exposures (weights) & “current” readouts

```DAX
-- Current weight for a given asset column (e.g., W_SAP.DE)
[Weight SAP] = AVERAGE ( Fact_PortfolioDaily[W_SAP.DE] )

-- “Top weights” table visual can list several of these measures side-by-side.
```

---

## 11) Formatting tips

* **\[Port Value]** → `0.00` (index), **\[% returns]** → `0.00%`, **\[VaR/ES]** → `0.00%`
* **\[Policy Rate (Last, %)]** → `0.00%` (already percent points; convert if needed)
* In cards, add subtitle: `As of: ` + `FORMAT([As Of Date],"yyyy-MM-dd")`.

---

## 12) Optional: pure-returns cumulative (if no PortValue)

> For completeness: compute cumulative return from daily returns inside DAX. Use with care (log sum approach).

```DAX
-- Cumulative return since start of selection from [Daily Return]
[Cumulative Return (log)] =
VAR T =
    FILTER ( ALLSELECTED ( 'Dim_Date'[Date] ),
             'Dim_Date'[Date] <= MAX ( 'Dim_Date'[Date] ) )
VAR ln_sum =
    SUMX ( T,
        VAR r = [Daily Return]
        RETURN IF ( r > -1, LN ( 1 + r ) )  -- guard against -100%
    )
RETURN EXP ( ln_sum ) - 1
```

---

### Notes

* Prefer **precomputed** rolling risk (vol/Sharpe/VaR/ES) for performance; keep DAX versions for small models or demos.
* Use **`ALLSELECTED`** in selection-aware measures (cards/lines) so slicers behave intuitively.
* For multi-strategy setups, add `Strat` column to facts and turn these measures into `CALCULATE(…, TREATAS())` per selection.

---

