-- Migration to create the map_config table
CREATE TABLE map_config (
  id SERIAL PRIMARY KEY,
  api_key TEXT NOT NULL,
  environment VARCHAR(10) NOT NULL CHECK (environment IN ('dev','stage','prod')),
  last_validated TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);