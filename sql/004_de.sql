INSERT INTO "worldTravelCountryRegions" (name, country_code)
VALUES
  ('Baden-Württemberg', 'de'),
  ('Bavaria', 'de'),
  ('Berlin', 'de'),
  ('Brandenburg', 'de'),
  ('Bremen', 'de'),
  ('Hamburg', 'de'),
  ('Hesse', 'de'),
  ('Lower Saxony', 'de'),
  ('Mecklenburg-Vorpommern', 'de'),
  ('North Rhine-Westphalia', 'de'),
  ('Rhineland-Palatinate', 'de'),
  ('Saarland', 'de'),
  ('Saxony', 'de'),
  ('Saxony-Anhalt', 'de'),
  ('Schleswig-Holstein', 'de'),
  ('Thuringia', 'de')

ON CONFLICT (name) DO NOTHING;
