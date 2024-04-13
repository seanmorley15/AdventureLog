INSERT INTO "worldTravelCountryRegions" (id, name, country_code)
VALUES
  ('FR-ARA', 'Auvergne-Rhône-Alpes', 'fr'),
  ('FR-BFC', 'Bourgogne-Franche-Comté', 'fr'),
  ('FR-BRE', 'Brittany', 'fr'),
  ('FR-CVL', 'Centre-Val de Loire', 'fr'),
  ('FR-GES', 'Grand Est', 'fr'),
  ('FR-HDF', 'Hauts-de-France', 'fr'),
  ('FR-IDF', 'Île-de-France', 'fr'),
  ('FR-NOR', 'Normandy', 'fr'),
  ('FR-NAQ', 'Nouvelle-Aquitaine', 'fr'),
  ('FR-OCC', 'Occitanie', 'fr'),
  ('FR-PDL', 'Pays de la Loire', 'fr'),
  ('FR-PAC', 'Provence-Alpes-Côte d''Azur', 'fr'),
  ('FR-COR', 'Corsica', 'fr'),
  ('FR-MQ', 'Martinique', 'fr'),
  ('FR-GF', 'French Guiana', 'fr'),
  ('FR-RÉ', 'Réunion', 'fr'),
  ('FR-YT', 'Mayotte', 'fr'),
  ('FR-GP', 'Guadeloupe', 'fr')

ON CONFLICT (id) DO NOTHING;