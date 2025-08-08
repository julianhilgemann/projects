import numpy as np
import pandas as pd
import os
from datetime import datetime

# ---------- CONFIG ----------
YEARS = 1
FREQ = 'H'
MONTE_CARLO_RUNS = 5
OUTPUT_DIR = "synthetic_timeseries"
np.random.seed(42)  # For reproducibility
# ----------------------------

def generate_single_series(years=YEARS, freq=FREQ, params=None):
    """Generate one synthetic time series with multiple seasonalities + AR noise."""
    # 1) Time index
    date_rng = pd.date_range(start="2020-01-01", periods=int(years * 365.25 * 24), freq=freq)
    n = len(date_rng)
    t = np.arange(n)

    # 2) Randomize parameters if not provided
    if params is None:
        params = {
            "trend_slope": np.random.uniform(0.0001, 0.001),
            "cycle_amplitude": np.random.uniform(5, 15),
            "cycle_period_hours": np.random.uniform(24*2000, 24*3000),  # long-term cycle
            "hourly_amp": np.random.uniform(1, 3),
            "daily_amp": np.random.uniform(2, 5),
            "weekly_amp": np.random.uniform(3, 6),
            "monthly_amp": np.random.uniform(4, 8),
            "ar_coef": np.random.uniform(0.3, 0.7),
            "noise_std": np.random.uniform(0.5, 2.0),
            "spike_prob": 0.002,
            "spike_magnitude": np.random.uniform(5, 15)
        }

    # 3) Components
    trend = params["trend_slope"] * t
    long_cycle = params["cycle_amplitude"] * np.sin(2 * np.pi * t / params["cycle_period_hours"])
    hourly = params["hourly_amp"] * np.sin(2 * np.pi * (t % 24) / 24)
    daily = params["daily_amp"] * np.sin(2 * np.pi * (t % (24*7)) / (24*1))  # daily cycle pattern
    weekly = params["weekly_amp"] * np.sin(2 * np.pi * (t % (24*7)) / (24*7))
    monthly = params["monthly_amp"] * np.sin(2 * np.pi * (t % (24*30)) / (24*30))

    # 4) AR(1) noise
    noise = np.zeros(n)
    for i in range(1, n):
        noise[i] = params["ar_coef"] * noise[i-1] + np.random.normal(0, params["noise_std"])

    # 5) Event spikes
    spikes = (np.random.rand(n) < params["spike_prob"]) * (
        np.random.choice([-1, 1], size=n) * params["spike_magnitude"]
    )

    # 6) Combine all
    y = trend + long_cycle + hourly + daily + weekly + monthly + noise + spikes

    # 7) DataFrame output
    df = pd.DataFrame({
        "timestamp": date_rng,
        "value": y
    })

    return df, params


def run_monte_carlo(runs=MONTE_CARLO_RUNS):
    """Run multiple simulations and save outputs + params."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_params = []

    for run in range(runs):
        df, params = generate_single_series()
        run_id = f"run_{run+1}"
        df.to_csv(f"{OUTPUT_DIR}/{run_id}.csv", index=False)

        params_record = {"run_id": run_id}
        params_record.update(params)
        all_params.append(params_record)

    # Save parameters for all runs
    pd.DataFrame(all_params).to_csv(f"{OUTPUT_DIR}/simulation_parameters.csv", index=False)
    print(f"Generated {runs} runs in '{OUTPUT_DIR}' folder.")


if __name__ == "__main__":
    run_monte_carlo()