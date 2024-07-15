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
	trip_id?: number | null;
	latitude: number | null;
	longitude: number | null;
	is_public: boolean;
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
};
