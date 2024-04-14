export interface Adventure {
  id: number;
  name: string;
  location: string;
  created: string;
}

export interface RegionInfo {
  name: string;
  abbreviation: string;
  description: string;
  capital: string;
  largest_city: string;
  area: {
    total: number;
    units: string;
  };
  population: {
    estimate: number;
    year: number;
  };
  state_flower: string;
  state_bird: string;
  state_tree: string;
  climate: {
    description: string;
    summer_highs: string;
    winter_lows: string;
    precipitation: string;
  };
  economy: {
    industries: string[];
    agricultural_products: string[];
  };
  tourism: {
    attractions: string[];
  };
  major_sports_teams: string[];
};
