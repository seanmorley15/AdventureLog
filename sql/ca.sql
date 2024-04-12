INSERT INTO "worldTravelCountryRegions" (name, country_code)
VALUES
  ('Alberta', 'ca'),
  ('British Columbia', 'ca'),
  ('Manitoba', 'ca'),
  ('New Brunswick', 'ca'),
  ('Newfoundland and Labrador', 'ca'),
  ('Nova Scotia', 'ca'),
  ('Ontario', 'ca'),
  ('Prince Edward Island', 'ca'),
  ('Quebec', 'ca'),
  ('Saskatchewan', 'ca'),
  ('Northwest Territories', 'ca'),
  ('Nunavut', 'ca'),
  ('Yukon', 'ca');

ON CONFLICT (name) DO NOTHING;
