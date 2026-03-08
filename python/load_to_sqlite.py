"""
load_to_sqlite.py
Loads all CSV/JSON data into a SQLite database and executes
the reporting queries from schema_and_queries.sql.
"""

import sqlite3
import pandas as pd
import json
import os


def main():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    data_dir = os.path.join(base_dir, "data")
    output_dir = os.path.join(base_dir, "output")
    sql_dir = os.path.join(base_dir, "sql")
    db_path = os.path.join(output_dir, "fund_reporting.db")

    # Remove existing DB
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ── Create schema ──
    print("Creating schema...")
    with open(os.path.join(sql_dir, "schema_and_queries.sql"), "r") as f:
        sql_content = f.read()

    # Extract CREATE TABLE statements
    import re
    # Remove SQL comments
    clean_sql = re.sub(r'--[^\n]*', '', sql_content)
    for statement in clean_sql.split(";"):
        statement = statement.strip()
        if statement.upper().startswith("CREATE TABLE"):
            cursor.execute(statement)
    conn.commit()

    # ── Load data ──
    print("Loading data...")

    # Fund metadata
    with open(os.path.join(data_dir, "fund_metadata.json"), "r") as f:
        meta = json.load(f)
    cursor.execute(
        "INSERT INTO fund_metadata VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("BRSGEQ", meta["fund_name"], meta["benchmark"], meta["inception_date"],
         meta["base_currency"], meta["strategy"], meta["domicile"], meta["fund_manager"])
    )

    # Sector returns (unpivot from wide to long)
    returns_df = pd.read_csv(os.path.join(data_dir, "sector_returns.csv"), parse_dates=["date"])
    sectors = [c for c in returns_df.columns if c != "date"]
    for _, row in returns_df.iterrows():
        for sector in sectors:
            cursor.execute(
                "INSERT INTO sector_returns VALUES (?, ?, ?)",
                (row["date"].strftime("%Y-%m-%d"), sector, row[sector])
            )

    # Sector weights
    weights_df = pd.read_csv(os.path.join(data_dir, "sector_weights.csv"), parse_dates=["date"])
    for _, row in weights_df.iterrows():
        cursor.execute(
            "INSERT INTO sector_weights VALUES (?, ?, ?, ?)",
            (row["date"].strftime("%Y-%m-%d"), row["sector"],
             row["fund_weight"], row["benchmark_weight"])
        )

    # Attribution output
    attr_df = pd.read_csv(os.path.join(output_dir, "sector_attribution.csv"), parse_dates=["date"])
    for _, row in attr_df.iterrows():
        cursor.execute(
            "INSERT INTO sector_attribution VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (row["date"].strftime("%Y-%m-%d"), row["sector"],
             row["fund_weight"], row["benchmark_weight"], row["active_weight"],
             row["fund_return"], row["benchmark_return"],
             row["allocation_effect"], row["selection_effect"],
             row["interaction_effect"], row["total_effect"])
        )

    # Monthly summary
    ms_df = pd.read_csv(os.path.join(output_dir, "monthly_summary.csv"), parse_dates=["date"])
    for _, row in ms_df.iterrows():
        cursor.execute(
            "INSERT INTO monthly_summary VALUES (?, ?, ?, ?, ?, ?, ?)",
            (row["date"].strftime("%Y-%m-%d"), row["fund_return"],
             row["benchmark_return"], row["active_return"],
             row["allocation_effect"], row["selection_effect"],
             row["interaction_effect"])
        )

    # AUM flows
    aum_df = pd.read_csv(os.path.join(data_dir, "aum_flows.csv"), parse_dates=["date"])
    for _, row in aum_df.iterrows():
        cursor.execute(
            "INSERT INTO aum_flows VALUES (?, ?, ?, ?, ?)",
            (row["date"].strftime("%Y-%m-%d"), row["aum_start_mm"],
             row["net_flows_mm"], row["market_return_pct"], row["aum_end_mm"])
        )

    conn.commit()
    print(f"Database created: {db_path}")

    # ── Run queries ──
    print("\n" + "=" * 60)
    print("RUNNING REPORTING QUERIES")
    print("=" * 60)

    queries = {
        "Query 1: Monthly Performance with Cumulative Returns": """
            SELECT date,
                ROUND(fund_return * 100, 2) AS fund_pct,
                ROUND(benchmark_return * 100, 2) AS bench_pct,
                ROUND(active_return * 100, 2) AS active_pct
            FROM monthly_summary ORDER BY date
        """,
        "Query 2: Full-Period Sector Attribution": """
            SELECT sector,
                ROUND(AVG(active_weight) * 100, 1) AS active_wt,
                ROUND(SUM(total_effect) * 100, 2) AS total_pct
            FROM sector_attribution
            GROUP BY sector ORDER BY total_pct DESC
        """,
        "Query 3: Top Contributors & Detractors": """
            SELECT * FROM (
                SELECT sector, ROUND(SUM(total_effect)*100,2) AS pct, 'Top' AS type
                FROM sector_attribution GROUP BY sector ORDER BY pct DESC LIMIT 3
            ) UNION ALL SELECT * FROM (
                SELECT sector, ROUND(SUM(total_effect)*100,2) AS pct, 'Bottom' AS type
                FROM sector_attribution GROUP BY sector ORDER BY pct ASC LIMIT 3
            )
        """,
        "Query 4: AUM & Flows Summary": """
            SELECT date, ROUND(aum_end_mm,1) AS aum, ROUND(net_flows_mm,1) AS flows,
                CASE WHEN net_flows_mm > 0 THEN 'Inflow' ELSE 'Outflow' END AS direction
            FROM aum_flows ORDER BY date
        """,
        "Query 6: Sectors with >50% Hit Rate": """
            SELECT sector,
                SUM(CASE WHEN total_effect > 0 THEN 1 ELSE 0 END) AS pos_months,
                COUNT(*) AS total,
                ROUND(SUM(total_effect)*100, 2) AS contribution_pct
            FROM sector_attribution GROUP BY sector
            HAVING pos_months * 1.0 / total > 0.5
            ORDER BY contribution_pct DESC
        """
    }

    for title, query in queries.items():
        print(f"\n{title}")
        print("-" * 50)
        result = pd.read_sql_query(query, conn)
        print(result.to_string(index=False))

    conn.close()
    print(f"\nAll queries executed. Database: {db_path}")


if __name__ == "__main__":
    main()
