-- ============================================================
-- Product Strategy Reporting: SQL Schema & Queries
-- Fund performance, attribution, and AUM/flows database
-- ============================================================

-- ────────────────────────────────────────────
-- SCHEMA
-- ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS fund_metadata (
    fund_id         TEXT PRIMARY KEY,
    fund_name       TEXT NOT NULL,
    benchmark       TEXT NOT NULL,
    inception_date  DATE,
    base_currency   TEXT DEFAULT 'USD',
    strategy        TEXT,
    domicile        TEXT,
    fund_manager    TEXT
);

CREATE TABLE IF NOT EXISTS sector_returns (
    date            DATE NOT NULL,
    sector          TEXT NOT NULL,
    sector_return   REAL NOT NULL,
    PRIMARY KEY (date, sector)
);

CREATE TABLE IF NOT EXISTS sector_weights (
    date              DATE NOT NULL,
    sector            TEXT NOT NULL,
    fund_weight       REAL NOT NULL,
    benchmark_weight  REAL NOT NULL,
    PRIMARY KEY (date, sector)
);

CREATE TABLE IF NOT EXISTS sector_attribution (
    date                DATE NOT NULL,
    sector              TEXT NOT NULL,
    fund_weight         REAL,
    benchmark_weight    REAL,
    active_weight       REAL,
    fund_return         REAL,
    benchmark_return    REAL,
    allocation_effect   REAL,
    selection_effect    REAL,
    interaction_effect  REAL,
    total_effect        REAL,
    PRIMARY KEY (date, sector)
);

CREATE TABLE IF NOT EXISTS monthly_summary (
    date              DATE PRIMARY KEY,
    fund_return       REAL NOT NULL,
    benchmark_return  REAL NOT NULL,
    active_return     REAL NOT NULL,
    allocation_effect REAL,
    selection_effect  REAL,
    interaction_effect REAL
);

CREATE TABLE IF NOT EXISTS aum_flows (
    date              DATE PRIMARY KEY,
    aum_start_mm      REAL,
    net_flows_mm      REAL,
    market_return_pct REAL,
    aum_end_mm        REAL
);


-- ────────────────────────────────────────────
-- QUERY 1: Monthly performance summary with
--          running cumulative returns
-- ────────────────────────────────────────────

SELECT
    date,
    ROUND(fund_return * 100, 2) AS fund_return_pct,
    ROUND(benchmark_return * 100, 2) AS benchmark_return_pct,
    ROUND(active_return * 100, 2) AS active_return_pct,
    ROUND((EXP(SUM(LN(1 + fund_return)) OVER (ORDER BY date)) - 1) * 100, 2)
        AS cum_fund_return_pct,
    ROUND((EXP(SUM(LN(1 + benchmark_return)) OVER (ORDER BY date)) - 1) * 100, 2)
        AS cum_benchmark_return_pct
FROM monthly_summary
ORDER BY date;


-- ────────────────────────────────────────────
-- QUERY 2: Full-period sector attribution
--          ranked by total contribution
-- ────────────────────────────────────────────

SELECT
    sector,
    ROUND(AVG(fund_weight) * 100, 1) AS avg_fund_weight_pct,
    ROUND(AVG(benchmark_weight) * 100, 1) AS avg_bm_weight_pct,
    ROUND(AVG(active_weight) * 100, 1) AS avg_active_weight_pct,
    ROUND(SUM(allocation_effect) * 100, 2) AS total_allocation_pct,
    ROUND(SUM(selection_effect) * 100, 2) AS total_selection_pct,
    ROUND(SUM(interaction_effect) * 100, 2) AS total_interaction_pct,
    ROUND(SUM(total_effect) * 100, 2) AS total_contribution_pct
FROM sector_attribution
GROUP BY sector
ORDER BY total_contribution_pct DESC;


-- ────────────────────────────────────────────
-- QUERY 3: Top 3 contributors and bottom 3
--          detractors by total effect
-- ────────────────────────────────────────────

SELECT * FROM (
    SELECT
        sector,
        ROUND(SUM(total_effect) * 100, 2) AS contribution_pct,
        'Contributor' AS category
    FROM sector_attribution
    GROUP BY sector
    ORDER BY contribution_pct DESC
    LIMIT 3
)
UNION ALL
SELECT * FROM (
    SELECT
        sector,
        ROUND(SUM(total_effect) * 100, 2) AS contribution_pct,
        'Detractor' AS category
    FROM sector_attribution
    GROUP BY sector
    ORDER BY contribution_pct ASC
    LIMIT 3
);


-- ────────────────────────────────────────────
-- QUERY 4: Monthly AUM with net flow direction
--          and cumulative net flows
-- ────────────────────────────────────────────

SELECT
    date,
    ROUND(aum_start_mm, 1) AS aum_start,
    ROUND(net_flows_mm, 1) AS net_flows,
    CASE
        WHEN net_flows_mm > 0 THEN 'Inflow'
        ELSE 'Outflow'
    END AS flow_direction,
    ROUND(SUM(net_flows_mm) OVER (ORDER BY date), 1) AS cum_net_flows,
    ROUND(aum_end_mm, 1) AS aum_end,
    ROUND((aum_end_mm / aum_start_mm - 1) * 100, 2) AS monthly_growth_pct
FROM aum_flows
ORDER BY date;


-- ────────────────────────────────────────────
-- QUERY 5: Allocation vs selection effect
--          breakdown by quarter
-- ────────────────────────────────────────────

SELECT
    CASE
        WHEN CAST(strftime('%m', date) AS INTEGER) BETWEEN 1 AND 3 THEN 'Q1'
        WHEN CAST(strftime('%m', date) AS INTEGER) BETWEEN 4 AND 6 THEN 'Q2'
        WHEN CAST(strftime('%m', date) AS INTEGER) BETWEEN 7 AND 9 THEN 'Q3'
        ELSE 'Q4'
    END AS quarter,
    strftime('%Y', date) AS year,
    ROUND(SUM(allocation_effect) * 100, 2) AS allocation_pct,
    ROUND(SUM(selection_effect) * 100, 2) AS selection_pct,
    ROUND(SUM(interaction_effect) * 100, 2) AS interaction_pct,
    ROUND(SUM(total_effect) * 100, 2) AS total_active_pct
FROM sector_attribution
GROUP BY year, quarter
ORDER BY year, quarter;


-- ────────────────────────────────────────────
-- QUERY 6: Sectors with consistent positive
--          attribution (positive in >50% months)
-- ────────────────────────────────────────────

SELECT
    sector,
    COUNT(*) AS total_months,
    SUM(CASE WHEN total_effect > 0 THEN 1 ELSE 0 END) AS positive_months,
    ROUND(SUM(CASE WHEN total_effect > 0 THEN 1.0 ELSE 0.0 END) / COUNT(*) * 100, 0)
        AS hit_rate_pct,
    ROUND(SUM(total_effect) * 100, 2) AS total_contribution_pct
FROM sector_attribution
GROUP BY sector
HAVING hit_rate_pct > 50
ORDER BY hit_rate_pct DESC, total_contribution_pct DESC;


-- ────────────────────────────────────────────
-- QUERY 7: Monthly active return decomposition
--          (verifies allocation + selection +
--           interaction = active return)
-- ────────────────────────────────────────────

SELECT
    ms.date,
    ROUND(ms.active_return * 100, 4) AS active_return_pct,
    ROUND(SUM(sa.allocation_effect) * 100, 4) AS sum_allocation_pct,
    ROUND(SUM(sa.selection_effect) * 100, 4) AS sum_selection_pct,
    ROUND(SUM(sa.interaction_effect) * 100, 4) AS sum_interaction_pct,
    ROUND((SUM(sa.allocation_effect) + SUM(sa.selection_effect) + SUM(sa.interaction_effect)) * 100, 4)
        AS reconstructed_active_pct,
    ROUND(ABS(ms.active_return - SUM(sa.allocation_effect) - SUM(sa.selection_effect) - SUM(sa.interaction_effect)) * 10000, 4)
        AS residual_bps
FROM monthly_summary ms
JOIN sector_attribution sa ON ms.date = sa.date
GROUP BY ms.date
ORDER BY ms.date;
