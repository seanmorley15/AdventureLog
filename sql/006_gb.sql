INSERT INTO "worldTravelCountryRegions" (id, name, country_code)
VALUES
  ('GB-ENG', 'England', 'gb'),
  ('GB-NIR', 'Northern Ireland', 'gb'),
  ('GB-SCT', 'Scotland', 'gb'),
  ('GB-WLS', 'Wales', 'gb')

ON CONFLICT (id) DO NOTHING;
