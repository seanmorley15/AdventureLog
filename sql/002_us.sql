INSERT INTO "worldTravelCountryRegions" (id, name, country_code)
VALUES
  ('US-AL', 'Alabama', 'us', '{
  "name": "Alabama",
  "abbreviation": "AL",
  "description": "Alabama is a state located in the southeastern region of the United States. Known for its rich history, including its role in the American Civil War and the Civil Rights Movement, Alabama offers a diverse landscape of mountains, plains, and coastal areas. The state boasts a humid subtropical climate and is known for its strong tradition in college sports, particularly football. Alabama's economy is diverse, with major industries including automotive manufacturing, agriculture, and aerospace. Tourists are drawn to Alabama's natural beauty, historical sites, and cultural landmarks.",
  "capital": "Montgomery",
  "largest_city": "Birmingham",
  "area": {
    "total": 52420,
    "units": "square miles"
  },
  "population": {
    "estimate": 4903185,
    "year": 2020
  },
  "state_flower": "Camellia",
  "state_bird": "Yellowhammer",
  "state_tree": "Southern Longleaf Pine",
  "climate": {
    "description": "Humid subtropical",
    "summer_highs": "80-90°F",
    "winter_lows": "30-50°F",
    "precipitation": "Abundant throughout the year"
  },
  "economy": {
    "industries": [
      "Automotive Manufacturing",
      "Agriculture",
      "Mining",
      "Technology",
      "Aerospace"
    ],
    "agricultural_products": [
      "Poultry",
      "Cotton",
      "Peanuts",
      "Soybeans",
      "Corn"
    ]
  },
  "tourism": {
    "attractions": [
      "U.S. Space & Rocket Center",
      "Gulf Shores and Orange Beach",
      "Rosa Parks Museum",
      "Civil Rights Institute",
      "Little River Canyon National Preserve"
    ]
  },
  "major_sports_teams": [
    "Alabama Crimson Tide (NCAA)",
    "Auburn Tigers (NCAA)"
  ]
}'),
  ('US-AK', 'Alaska', 'us'),
  ('US-AZ', 'Arizona', 'us'),
  ('US-AR', 'Arkansas', 'us'),
  ('US-CA', 'California', 'us'),
  ('US-CO', 'Colorado', 'us'),
  ('US-CT', 'Connecticut', 'us'),
  ('US-DE', 'Delaware', 'us'),
  ('US-FL', 'Florida', 'us'),
  ('US-GA', 'Georgia', 'us'),
  ('US-HI', 'Hawaii', 'us'),
  ('US-ID', 'Idaho', 'us'),
  ('US-IL', 'Illinois', 'us'),
  ('US-IN', 'Indiana', 'us'),
  ('US-IA', 'Iowa', 'us'),
  ('US-KS', 'Kansas', 'us'),
  ('US-KY', 'Kentucky', 'us'),
  ('US-LA', 'Louisiana', 'us'),
  ('US-ME', 'Maine', 'us'),
  ('US-MD', 'Maryland', 'us'),
  ('US-MA', 'Massachusetts', 'us'),
  ('US-MI', 'Michigan', 'us'),
  ('US-MN', 'Minnesota', 'us'),
  ('US-MS', 'Mississippi', 'us'),
  ('US-MO', 'Missouri', 'us'),
  ('US-MT', 'Montana', 'us'),
  ('US-NE', 'Nebraska', 'us'),
  ('US-NV', 'Nevada', 'us'),
  ('US-NH', 'New Hampshire', 'us'),
  ('US-NJ', 'New Jersey', 'us'),
  ('US-NM', 'New Mexico', 'us'),
  ('US-NY', 'New York', 'us'),
  ('US-NC', 'North Carolina', 'us'),
  ('US-ND', 'North Dakota', 'us'),
  ('US-OH', 'Ohio', 'us'),
  ('US-OK', 'Oklahoma', 'us'),
  ('US-OR', 'Oregon', 'us'),
  ('US-PA', 'Pennsylvania', 'us'),
  ('US-RI', 'Rhode Island', 'us'),
  ('US-SC', 'South Carolina', 'us'),
  ('US-SD', 'South Dakota', 'us'),
  ('US-TN', 'Tennessee', 'us'),
  ('US-TX', 'Texas', 'us'),
  ('US-UT', 'Utah', 'us'),
  ('US-VT', 'Vermont', 'us'),
  ('US-VA', 'Virginia', 'us'),
  ('US-WA', 'Washington', 'us'),
  ('US-WV', 'West Virginia', 'us'),
  ('US-WI', 'Wisconsin', 'us'),
  ('US-WY', 'Wyoming', 'us')
ON CONFLICT (id) DO NOTHING;
