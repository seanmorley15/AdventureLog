INSERT INTO "worldTravelCountryRegions" (id, name, country_code)
VALUES
  ('DE-BW', 'Baden-Württemberg', 'de'),
  ('DE-BY', 'Bavaria', 'de'),
  ('DE-BE', 'Berlin', 'de'),
  ('DE-BB', 'Brandenburg', 'de'),
  ('DE-HB', 'Bremen', 'de'),
  ('DE-HH', 'Hamburg', 'de'),
  ('DE-HE', 'Hesse', 'de'),
  ('DE-NI', 'Lower Saxony', 'de'),
  ('DE-MV', 'Mecklenburg-Vorpommern', 'de'),
  ('DE-NW', 'North Rhine-Westphalia', 'de'),
  ('DE-RP', 'Rhineland-Palatinate', 'de'),
  ('DE-SL', 'Saarland', 'de'),
  ('DE-SN', 'Saxony', 'de'),
  ('DE-ST', 'Saxony-Anhalt', 'de'),
  ('DE-SH', 'Schleswig-Holstein', 'de'),
  ('DE-TH', 'Thuringia', 'de')

ON CONFLICT (id) DO NOTHING;
