INSERT INTO "worldTravelCountryRegions" (id, name, country_code)
VALUES
  ('CA-AB', 'Alberta', 'ca'),
  ('CA-BC', 'British Columbia', 'ca'),
  ('CA-MB', 'Manitoba', 'ca'),
  ('CA-NB', 'New Brunswick', 'ca'),
  ('CA-NL', 'Newfoundland and Labrador', 'ca'),
  ('CA-NS', 'Nova Scotia', 'ca'),
  ('CA-ON', 'Ontario', 'ca'),
  ('CA-PE', 'Prince Edward Island', 'ca'),
  ('CA-QC', 'Quebec', 'ca'),
  ('CA-SK', 'Saskatchewan', 'ca'),
  ('CA-NT', 'Northwest Territories', 'ca'),
  ('CA-NU', 'Nunavut', 'ca'),
  ('CA-YT', 'Yukon', 'ca')
ON CONFLICT (id) DO NOTHING;
