-- Daily KPI tracking table
-- Mirrors the structure of Ash's 2026 Tracker Google Sheet
-- One row per working day; ratios are computed at query time

CREATE TABLE IF NOT EXISTS daily_kpis (
  id                      BIGSERIAL PRIMARY KEY,
  date                    DATE UNIQUE NOT NULL,

  -- Seller activity
  contacts                INT NOT NULL DEFAULT 0,
  leads                   INT NOT NULL DEFAULT 0,
  emails                  INT NOT NULL DEFAULT 0,
  appts_set               INT NOT NULL DEFAULT 0,
  appts_met               INT NOT NULL DEFAULT 0,
  fsbo_preview_set        INT NOT NULL DEFAULT 0,
  fsbo_met                INT NOT NULL DEFAULT 0,
  fsbo_listing            INT NOT NULL DEFAULT 0,
  listings_other          INT NOT NULL DEFAULT 0,  -- Listings From Other Sources
  listings                INT NOT NULL DEFAULT 0,

  -- Buyer activity
  buyer_appts_set         INT NOT NULL DEFAULT 0,
  buyer_appts_met         INT NOT NULL DEFAULT 0,
  buyer_contracts_signed  INT NOT NULL DEFAULT 0,

  -- Closings (seller + buyer combined)
  closings                INT NOT NULL DEFAULT 0,

  notes                   TEXT,

  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Auto-update updated_at on any row change
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS daily_kpis_updated_at ON daily_kpis;
CREATE TRIGGER daily_kpis_updated_at
  BEFORE UPDATE ON daily_kpis
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
