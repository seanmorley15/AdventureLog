INSERT INTO "worldTravelCountryRegions" (id, name, country_code)
VALUES
  ('AU-NSW', 'New South Wales', 'au'),
  ('AU-VIC', 'Victoria', 'au'),
  ('AU-QLD', 'Queensland', 'au'),
  ('AU-SA', 'South Australia', 'au'),
  ('AU-WA', 'Western Australia', 'au'),
  ('AU-TAS', 'Tasmania', 'au'),
  ('AU-NT', 'Northern Territory', 'au'),
  ('AU-ACT', 'Australian Capital Territory', 'au')

ON CONFLICT (id) DO NOTHING;
