import { VALID_TIMEZONES } from './dateUtils';

export type User = {
	pk: number;
	username: string;
	first_name: string | null;
	last_name: string | null;
	date_joined: string | null;
	is_staff: boolean;
	profile_pic: string | null;
	uuid: string;
	public_profile: boolean;
	has_password: boolean;
	disable_password: boolean;
};

export type Adventure = {
	id: string;
	user_id: string | null;
	name: string;
	location?: string | null;
	activity_types?: string[] | null;
	description?: string | null;
	rating?: number | null;
	link?: string | null;
	images: {
		id: string;
		image: string;
		is_primary: boolean;
		immich_id: string | null;
	}[];
	visits: {
		id: string;
		start_date: string;
		end_date: string;
		timezone: string | null;
		notes: string;
	}[];
	collection?: string | null;
	latitude: number | null;
	longitude: number | null;
	is_public: boolean;
	created_at?: string | null;
	updated_at?: string | null;
	is_visited?: boolean;
	category: Category | null;
	attachments: Attachment[];
	user?: User | null;
	city?: City | null;
	region?: Region | null;
	country?: Country | null;
};

export type AdditionalAdventure = Adventure & {
	sun_times: {
		date: string;
		visit_id: string;
		sunrise: string;
		sunset: string;
	}[];
};

export type Country = {
	id: number;
	name: string;
	country_code: string;
	subregion: string;
	flag_url: string;
	capital: string;
	num_regions: number;
	num_visits: number;
	longitude: number | null;
	latitude: number | null;
};

export type Region = {
	id: string;
	name: string;
	country: string;
	latitude: number;
	longitude: number;
	num_cities: number;
	country_name: string;
};

export type City = {
	id: string;
	name: string;
	latitude: number | null;
	longitude: number | null;
	region: string;
	region_name: string;
	country_name: string;
};

export type VisitedRegion = {
	id: number;
	region: string;
	user_id: string;
	longitude: number;
	latitude: number;
	name: string;
};

export type VisitedCity = {
	id: number;
	city: string;
	user_id: string;
	longitude: number;
	latitude: number;
	name: string;
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
	user_id: string;
	name: string;
	description: string;
	is_public: boolean;
	adventures: Adventure[];
	created_at?: string | null;
	start_date: string | null;
	end_date: string | null;
	transportations?: Transportation[];
	notes?: Note[];
	lodging?: Lodging[];
	checklists?: Checklist[];
	is_archived?: boolean;
	shared_with: string[] | undefined;
	link?: string | null;
};

export type GeocodeSearchResult = {
	lat?: string;
	lon?: string;
	category?: string;
	type?: string;
	importance?: number;
	addresstype?: string;
	name?: string;
	display_name?: string;
};

export type Transportation = {
	id: string;
	user_id: string;
	type: string;
	name: string;
	description: string | null;
	rating: number | null;
	link: string | null;
	date: string | null; // ISO 8601 date string
	end_date: string | null; // ISO 8601 date string
	start_timezone: string | null;
	end_timezone: string | null;
	flight_number: string | null;
	from_location: string | null;
	to_location: string | null;
	origin_latitude: number | null;
	origin_longitude: number | null;
	destination_latitude: number | null;
	destination_longitude: number | null;
	is_public: boolean;
	distance: number | null; // in kilometers
	collection: Collection | null | string;
	created_at: string; // ISO 8601 date string
	updated_at: string; // ISO 8601 date string
};

export type Note = {
	id: string;
	user_id: string;
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
	user_id: string;
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
	user_id: string;
	name: string;
	is_checked: boolean;
	checklist: number;
	created_at: string; // ISO 8601 date string
	updated_at: string; // ISO 8601 date string
};

export type Background = {
	url: string;
	author?: string;
	location?: string;
};

export type ReverseGeocode = {
	region_id: string;
	region: string;
	country: string;
	region_visited: boolean;
	city_visited: boolean;
	display_name: string;
	city: string;
	city_id: string;
	location_name: string;
};

export type Category = {
	id: string;
	name: string;
	display_name: string;
	icon: string;
	user_id: string;
	num_adventures?: number | null;
};

export type ImmichIntegration = {
	id: string;
	server_url: string;
	api_key: string;
	copy_locally: boolean;
};

export type ImmichAlbum = {
	albumName: string;
	description: string;
	albumThumbnailAssetId: string;
	createdAt: string;
	updatedAt: string;
	id: string;
	ownerId: string;
	owner: {
		id: string;
		email: string;
		name: string;
		profileImagePath: string;
		avatarColor: string;
		profileChangedAt: string;
	};
	albumUsers: any[];
	shared: boolean;
	hasSharedLink: boolean;
	startDate: string;
	endDate: string;
	assets: any[];
	assetCount: number;
	isActivityEnabled: boolean;
	order: string;
	lastModifiedAssetTimestamp: string;
};

export type Attachment = {
	id: string;
	file: string;
	adventure: string;
	extension: string;
	user_id: string;
	name: string;
};

export type Lodging = {
	id: string;
	user_id: string;
	name: string;
	type: string;
	description: string | null;
	rating: number | null;
	link: string | null;
	check_in: string | null; // ISO 8601 date string
	check_out: string | null; // ISO 8601 date string
	timezone: string | null;
	reservation_number: string | null;
	price: number | null;
	latitude: number | null;
	longitude: number | null;
	location: string | null;
	is_public: boolean;
	collection: string | null;
	created_at: string; // ISO 8601 date string
	updated_at: string; // ISO 8601 date string
};
