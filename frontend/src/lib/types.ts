export type User = {
	pk: number;
	username: string;
	email: string | null;
	first_name: string | null;
	last_name: string | null;
	date_joined: string | null;
	is_staff: boolean;
	profile_pic: string | null;
	uuid: string;
	public_profile: boolean;
};

export type Adventure = {
	id: string;
	user_id: number | null;
	type: string;
	name: string;
	location?: string | null;
	activity_types?: string[] | null;
	description?: string | null;
	rating?: number | null;
	link?: string | null;
	images: {
		id: string;
		image: string;
	}[];
	visits: {
		id: string;
		start_date: string;
		end_date: string;
		notes: string;
	}[];
	collection?: string | null;
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
	subregion: string;
	flag_url: string;
	capital: string;
};

export type Region = {
	id: number;
	name: string;
	country: number;
	latitude: number;
	longitude: number;
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
	location: string;
	activity_type: string;
};

export type Collection = {
	id: string;
	user_id: number;
	name: string;
	description: string;
	is_public: boolean;
	adventures: Adventure[];
	created_at?: string;
	start_date?: string;
	end_date?: string;
	transportations?: Transportation[];
	notes?: Note[];
	checklists?: Checklist[];
	is_archived?: boolean;
	shared_with: string[];
	link?: string | null;
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
	id: string;
	user_id: number;
	type: string;
	name: string;
	description: string | null;
	rating: number | null;
	link: string | null;
	date: string | null; // ISO 8601 date string
	end_date: string | null; // ISO 8601 date string
	flight_number: string | null;
	from_location: string | null;
	to_location: string | null;
	is_public: boolean;
	collection: Collection | null;
	created_at: string; // ISO 8601 date string
	updated_at: string; // ISO 8601 date string
};

export type Note = {
	id: string;
	user_id: number;
	name: string;
	content: string | null;
	links: string[] | null;
	date: string | null; // ISO 8601 date string
	is_public: boolean;
	collection: number | null;
	created_at: string; // ISO 8601 date string
	updated_at: string; // ISO 8601 date string
};

export type Checklist = {
	id: string;
	user_id: number;
	name: string;
	items: ChecklistItem[];
	date: string | null; // ISO 8601 date string
	is_public: boolean;
	collection: number | null;
	created_at: string; // ISO 8601 date string
	updated_at: string; // ISO 8601 date string
};

export type ChecklistItem = {
	id: string;
	user_id: number;
	name: string;
	is_checked: boolean;
	checklist: number;
	created_at: string; // ISO 8601 date string
	updated_at: string; // ISO 8601 date string
};
