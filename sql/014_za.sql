INSERT INTO "worldTravelCountryRegions" (id, name, country_code)
VALUES
  ('ZA-EC', 'Eastern Cape', 'za'),
  ('ZA-FS', 'Free State', 'za'),
  ('ZA-GP', 'Gauteng', 'za'),
  ('ZA-KZN', 'KwaZulu-Natal', 'za'),
  ('ZA-LP', 'Limpopo', 'za'),
  ('ZA-MP', 'Mpumalanga', 'za'),
  ('ZA-NW', 'North West', 'za'),
  ('ZA-NC', 'Northern Cape', 'za'),
  ('ZA-WC', 'Western Cape', 'za')

ON CONFLICT (id) DO NOTHING;
