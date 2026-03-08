"""
generate_sample_data.py
Generates synthetic but realistic monthly performance and holdings data
for a systematic equity fund benchmarked against MSCI World.

Data covers 12 months (Jul 2025 - Jun 2026) with sector-level detail.
"""

import pandas as pd
import numpy as np
import os
import json
from datetime import datetime

np.random.seed(42)

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

SECTORS = [
    "Information Technology",
    "Health Care",
    "Financials",
    "Consumer Discretionary",
    "Industrials",
    "Communication Services",
    "Consumer Staples",
    "Energy",
    "Materials",
    "Utilities",
    "Real Estate"
]

MONTHS = pd.date_range("2025-07-01", periods=12, freq="MS")

# Benchmark weights (approximate MSCI World weights)
BENCHMARK_WEIGHTS = {
    "Information Technology": 0.235,
    "Health Care": 0.125,
    "Financials": 0.155,
    "Consumer Discretionary": 0.105,
    "Industrials": 0.110,
    "Communication Services": 0.075,
    "Consumer Staples": 0.065,
    "Energy": 0.045,
    "Materials": 0.040,
    "Utilities": 0.025,
    "Real Estate": 0.020
}

# Fund overweights/underweights vs benchmark (systematic alpha tilts)
FUND_TILTS = {
    "Information Technology": +0.045,
    "Health Care": +0.020,
    "Financials": -0.025,
    "Consumer Discretionary": +0.015,
    "Industrials": -0.010,
    "Communication Services": +0.010,
    "Consumer Staples": -0.025,
    "Energy": -0.015,
    "Materials": -0.005,
    "Utilities": -0.005,
    "Real Estate": -0.005
}

# ─────────────────────────────────────────────
# GENERATE MONTHLY SECTOR RETURNS
# ─────────────────────────────────────────────

def generate_sector_returns(months, sectors):
    """Generate realistic monthly sector returns with correlation structure."""
    n_months = len(months)
    n_sectors = len(sectors)

    # Base market return each month (mean ~0.8% monthly, vol ~4%)
    market_returns = np.random.normal(0.008, 0.04, n_months)

    # Sector-specific returns with market beta and idiosyncratic component
    betas = {
        "Information Technology": 1.15,
        "Health Care": 0.85,
        "Financials": 1.10,
        "Consumer Discretionary": 1.20,
        "Industrials": 1.05,
        "Communication Services": 1.00,
        "Consumer Staples": 0.65,
        "Energy": 0.90,
        "Materials": 1.00,
        "Utilities": 0.55,
        "Real Estate": 0.75
    }

    returns = {}
    for sector in sectors:
        beta = betas[sector]
        idio = np.random.normal(0, 0.02, n_months)
        returns[sector] = market_returns * beta + idio

    return pd.DataFrame(returns, index=months)


def generate_holdings_weights(months, sectors, benchmark_weights, fund_tilts):
    """Generate monthly fund and benchmark sector weights."""
    records = []
    for month in months:
        for sector in sectors:
            bm_w = benchmark_weights[sector]
            # Add small random drift to weights each month
            bm_noise = np.random.normal(0, 0.005)
            fund_noise = np.random.normal(0, 0.003)

            bm_weight = max(0.005, bm_w + bm_noise)
            fund_weight = max(0.005, bm_w + fund_tilts[sector] + fund_noise)

            records.append({
                "date": month,
                "sector": sector,
                "fund_weight": fund_weight,
                "benchmark_weight": bm_weight
            })

    df = pd.DataFrame(records)

    # Normalize weights to sum to 1.0 each month
    for month in months:
        mask = df["date"] == month
        df.loc[mask, "fund_weight"] = (
            df.loc[mask, "fund_weight"] / df.loc[mask, "fund_weight"].sum()
        )
        df.loc[mask, "benchmark_weight"] = (
            df.loc[mask, "benchmark_weight"] / df.loc[mask, "benchmark_weight"].sum()
        )

    return df


def generate_aum_flows(months):
    """Generate monthly AUM and flows data."""
    records = []
    aum = 2450.0  # Starting AUM in $M

    for i, month in enumerate(months):
        # Monthly flows: mix of inflows and occasional outflows
        if np.random.random() > 0.25:
            flow = np.random.uniform(10, 80)
        else:
            flow = np.random.uniform(-40, -5)

        # Market return effect on AUM
        mkt_return = np.random.normal(0.008, 0.03)
        aum_start = aum
        aum = aum * (1 + mkt_return) + flow

        records.append({
            "date": month,
            "aum_start_mm": round(aum_start, 1),
            "net_flows_mm": round(flow, 1),
            "market_return_pct": round(mkt_return * 100, 2),
            "aum_end_mm": round(aum, 1)
        })

    return pd.DataFrame(records)


def generate_fund_metadata():
    """Generate fund metadata."""
    return {
        "fund_name": "BlackRock Systematic Global Equity Fund",
        "fund_ticker": "BRSGEQ",
        "benchmark": "MSCI World Index",
        "inception_date": "2019-03-15",
        "base_currency": "USD",
        "fund_manager": "BlackRock Systematic (BSYS)",
        "strategy": "Systematic Equity - Multi-Factor",
        "domicile": "Ireland",
        "reporting_period": "Jul 2025 - Jun 2026",
        "total_aum_mm": 2650.0
    }


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(output_dir, exist_ok=True)

    # 1. Sector returns
    returns_df = generate_sector_returns(MONTHS, SECTORS)
    returns_df.index.name = "date"
    returns_df.to_csv(os.path.join(output_dir, "sector_returns.csv"))
    print(f"Generated sector_returns.csv: {returns_df.shape}")

    # 2. Holdings weights
    weights_df = generate_holdings_weights(MONTHS, SECTORS, BENCHMARK_WEIGHTS, FUND_TILTS)
    weights_df.to_csv(os.path.join(output_dir, "sector_weights.csv"), index=False)
    print(f"Generated sector_weights.csv: {weights_df.shape}")

    # 3. AUM and flows
    aum_df = generate_aum_flows(MONTHS)
    aum_df.to_csv(os.path.join(output_dir, "aum_flows.csv"), index=False)
    print(f"Generated aum_flows.csv: {aum_df.shape}")

    # 4. Fund metadata
    metadata = generate_fund_metadata()
    with open(os.path.join(output_dir, "fund_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
    print("Generated fund_metadata.json")

    print("\nAll sample data generated successfully.")
