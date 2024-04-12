INSERT INTO "worldTravelCountries" (name, country_code, continent)
VALUES
  ('United States', 'us', 'North America'),
  ('Canada', 'ca', 'North America'),
  ('Mexico', 'mx', 'North America'),
  ('Brazil', 'br', 'South America'),
  ('Argentina', 'ar', 'South America'),
  ('United Kingdom', 'gb', 'Europe'),
  ('Germany', 'de', 'Europe'),
  ('France', 'fr', 'Europe'),
  ('Japan', 'jp', 'Asia'),
  ('China', 'cn', 'Asia'),
  ('India', 'in', 'Asia'),
  ('Australia', 'au', 'Oceania'),
  ('New Zealand', 'nz', 'Oceania'),
  ('South Africa', 'za', 'Africa'),
  ('Egypt', 'eg', 'Africa'),
ON CONFLICT (country_code) DO NOTHING;