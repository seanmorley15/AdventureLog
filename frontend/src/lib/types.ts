export type User = {
	pk: number;
	username: string;
	email: string | null;
	first_name: string | null;
	last_name: string | null;
	date_joined: string | null;
	is_staff: boolean;
	profile_pic: string | null;
};

export type Adventure = {
	id: number;
	user_id: number;
	type: string;
	name: string;
	location?: string | null;
	activity_types?: string[] | null;
	description?: string | null;
	rating?: number | null;
	link?: string | null;
	image?: string | null;
	date?: string | null; // Assuming date is a string in 'YYYY-MM-DD' format
	collection?: number | null;
	latitude: number | null;
	longitude: number | null;
	is_public: boolean;
	created_at?: string | null;
	updated_at?: string | null;
};

export type Country = {
	id: number;
	name: string;
	country_code: string;
	continent: string;
};

export type Region = {
	id: number;
	name: string;
	country: number;
};

export type VisitedRegion = {
	id: number;
	region: number;
	user_id: number;
};

export type Point = {
	lngLat: {
		lat: number;
		lng: number;
	};
	name: string;
};

export type Collection = {
	id: number;
	user_id: number;
	name: string;
	description: string;
	is_public: boolean;
	adventures: Adventure[];
	created_at?: string;
	start_date?: string;
	end_date?: string;
	transportations?: Transportation[];
};

export type OpenStreetMapPlace = {
	place_id: number;
	licence: string;
	osm_type: string;
	osm_id: number;
	lat: string;
	lon: string;
	category: string;
	type: string;
	place_rank: number;
	importance: number;
	addresstype: string;
	name: string;
	display_name: string;
	boundingbox: string[];
};

export type Transportation = {
	id: number;
	user_id: number;
	type: string;
	name: string;
	description: string | null;
	rating: number | null;
	link: string | null;
	date: string | null; // ISO 8601 date string
	flight_number: string | null;
	from_location: string | null;
	to_location: string | null;
	is_public: boolean;
	collection: Collection | null;
	created_at: string; // ISO 8601 date string
	updated_at: string; // ISO 8601 date string
};
