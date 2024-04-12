INSERT INTO "worldTravelCountryRegions" (id, name, country_code)
VALUES
  ('NZ-N', 'Northland', 'nz'),
  ('NZ-AUK', 'Auckland', 'nz'),
  ('NZ-WKO', 'Waikato', 'nz'),
  ('NZ-BOP', 'Bay of Plenty', 'nz'),
  ('NZ-GIS', 'Gisborne', 'nz'),
  ('NZ-HKB', 'Hawke''s Bay', 'nz'),
  ('NZ-TKI', 'Taranaki', 'nz'),
  ('NZ-MWT', 'Manawatū-Whanganui', 'nz'),
  ('NZ-WGN', 'Wellington', 'nz'),
  ('NZ-TAS', 'Tasman', 'nz'),
  ('NZ-NEL', 'Nelson', 'nz'),
  ('NZ-MBH', 'Marlborough', 'nz'),
  ('NZ-WTC', 'West Coast', 'nz'),
  ('NZ-CAN', 'Canterbury', 'nz'),
  ('NZ-OTA', 'Otago', 'nz'),
  ('NZ-STL', 'Southland', 'nz')

ON CONFLICT (id) DO NOTHING;
