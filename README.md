# Product Strategy Reporting Pipeline

**Performance attribution, automated factsheet generation, and fund reporting for a systematic equity strategy.**

Built to demonstrate the technical workflow behind product strategy reporting at an asset manager: ingesting fund and benchmark data, running Brinson performance attribution, generating client-ready Excel factsheets, and querying a structured reporting database.

---

## Context

Product Strategists at asset managers translate complex investment data into client-facing materials -- presentations, factsheets, commentaries, and RFI responses. This pipeline automates the data and reporting backbone of that workflow.

**Fund modelled:** BlackRock Systematic Global Equity Fund (synthetic data)  
**Benchmark:** MSCI World Index  
**Period:** Jul 2025 -- Jun 2026  
**Sectors:** 11 GICS sectors with realistic weight tilts and return profiles

---

## Architecture

```
generate_sample_data.py     Synthetic fund/benchmark data (returns, weights, AUM/flows)
        |
performance_attribution.py  Brinson-Hood-Beebower attribution engine
        |
generate_factsheet.py       Formatted Excel factsheet (openpyxl)
load_to_sqlite.py           SQLite database + reporting queries
        |
FactsheetFormatter.bas      VBA: formatting, data refresh, commentary, PDF export
schema_and_queries.sql      7 SQL queries for recurring reporting
```

---

## Components

### Python

**generate_sample_data.py**  
Generates 12 months of synthetic but realistic data: sector-level returns (with beta and idiosyncratic components), fund and benchmark weights (with systematic tilts and monthly drift), AUM/flows, and fund metadata. All data normalised and saved as CSV/JSON.

**performance_attribution.py**  
Implements the Brinson-Hood-Beebower (BHB) single-period attribution model:
- **Allocation Effect:** Value from sector weight differences vs benchmark
- **Selection Effect:** Value from security selection within sectors
- **Interaction Effect:** Combined weight and return impact

Also calculates cumulative performance, annualised risk metrics (volatility, tracking error, information ratio, Sharpe ratio, max drawdown), and identifies top contributors/detractors.

**generate_factsheet.py**  
Produces a 4-tab Excel workbook using openpyxl:
- **Summary:** Key metrics, monthly returns table, cumulative performance line chart
- **Sector Attribution:** Full Brinson decomposition with conditional formatting and bar chart
- **Monthly Detail:** Sector-level heatmap of monthly attribution effects
- **AUM & Flows:** Asset tracking with flow direction and AUM trend chart

**load_to_sqlite.py**  
Loads all data into a SQLite database and executes 7 reporting queries covering cumulative returns, sector attribution rankings, contributor/detractor analysis, AUM trends, quarterly breakdowns, hit rates, and attribution reconciliation.

### VBA

**FactsheetFormatter.bas**  
5-module VBA automation for the Excel factsheet production cycle:
1. **FormatFactsheet:** Applies client-ready formatting with conditional colouring for positive/negative values
2. **RefreshDataLinks:** Imports updated CSV data from the Python pipeline output
3. **GenerateCommentary:** Auto-generates a performance narrative from portfolio data
4. **ExportToPDF:** Exports all sheets to a dated PDF for distribution
5. **RunFullRefresh:** Master routine executing the full refresh cycle (data > format > commentary > PDF)

### SQL

**schema_and_queries.sql**  
6 tables and 7 queries:
1. Monthly performance with running cumulative returns
2. Full-period sector attribution ranked by contribution
3. Top 3 contributors and bottom 3 detractors
4. AUM and flows with cumulative net flow tracking
5. Quarterly allocation vs selection breakdown
6. Sectors with consistent positive attribution (>50% hit rate)
7. Monthly attribution reconciliation check (allocation + selection + interaction = active return)

---

## Output Sample

**Performance Summary (12-month period):**

| Metric | Value |
|---|---|
| Cumulative Fund Return | 22.29% |
| Cumulative Benchmark Return | 20.42% |
| Active Return | +1.87% |
| Tracking Error | 0.76% |
| Information Ratio | 2.46x |
| Sharpe Ratio | 1.53x |
| Max Drawdown | -1.90% |

**Top Contributors:** Financials (+0.45%), Information Technology (+0.33%), Consumer Staples (+0.31%)  
**Top Detractors:** Industrials (-0.04%), Materials (-0.03%)

---

## How to Run

```bash
# 1. Generate sample data
python python/generate_sample_data.py

# 2. Run attribution engine
python python/performance_attribution.py

# 3. Generate Excel factsheet
python python/generate_factsheet.py

# 4. Load to SQLite and run queries
python python/load_to_sqlite.py
```

**Requirements:** Python 3.8+, pandas, numpy, openpyxl

**VBA:** Import `vba/FactsheetFormatter.bas` into the generated Excel workbook. Run `RunFullRefresh` to execute the full production cycle.

---

## File Structure

```
product-strategy-reporting/
|-- python/
|   |-- generate_sample_data.py
|   |-- performance_attribution.py
|   |-- generate_factsheet.py
|   |-- load_to_sqlite.py
|-- vba/
|   |-- FactsheetFormatter.bas
|-- sql/
|   |-- schema_and_queries.sql
|-- data/
|   |-- sector_returns.csv
|   |-- sector_weights.csv
|   |-- aum_flows.csv
|   |-- fund_metadata.json
|-- output/
|   |-- sector_attribution.csv
|   |-- monthly_summary.csv
|   |-- cumulative_performance.csv
|   |-- risk_metrics.json
|   |-- fund_reporting.db
|   |-- Fund_Factsheet_Report.xlsx
|-- README.md
```
