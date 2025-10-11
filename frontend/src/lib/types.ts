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
	measurement_system: 'metric' | 'imperial';
};

export type ContentImage = {
	id: string;
	image: string;
	is_primary: boolean;
	immich_id: string | null;
};

export type Location = {
	id: string;
	name: string;
	location?: string | null;
	tags?: string[] | null;
	description?: string | null;
	rating?: number | null;
	link?: string | null;
	images: ContentImage[];
	visits: Visit[];
	collections?: string[] | null;
	latitude: number | null;
	longitude: number | null;
	is_public: boolean;
	created_at?: string | null;
	updated_at?: string | null;
	is_visited?: boolean;
	category: Category | null;
	attachments: Attachment[];
	user: User | null;
	city?: City | null;
	region?: Region | null;
	country?: Country | null;
	trails: Trail[];
};

export type AdditionalLocation = Location & {
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
	user: string;
	longitude: number;
	latitude: number;
	name: string;
};

export type VisitedCity = {
	id: number;
	city: string;
	user: string;
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
	user: string;
	name: string;
	description: string;
	is_public: boolean;
	locations: Location[];
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

export type SlimCollection = {
	id: string;
	user: string;
	name: string;
	description: string;
	is_public: boolean;
	start_date: string | null;
	end_date: string | null;
	is_archived: boolean;
	link: string | null;
	created_at: string;
	updated_at: string;
	location_images: ContentImage[];
	location_count: number;
	shared_with: string[];
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
	user: string;
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
	images: ContentImage[]; // Array of images associated with the transportation
	attachments: Attachment[]; // Array of attachments associated with the transportation
};

export type Note = {
	id: string;
	user: string;
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
	user: string;
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
	user: string;
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
	user: string;
	num_locations?: number | null;
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
	extension: string;
	user: string;
	name: string;
	geojson: any | null; // GeoJSON representation of the attachment if the file is a GPX
};

export type Lodging = {
	id: string;
	user: string;
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
	images: ContentImage[]; // Array of images associated with the lodging
	attachments: Attachment[]; // Array of attachments associated with the lodging
};

export type CollectionInvite = {
	id: string;
	collection: string; // UUID of the collection
	name: string; // Name of the collection
	created_at: string; // ISO 8601 date string
	collection_owner_username: string; // Username of the collection owner
	collection_user_first_name: string; // First name of the collection user
	collection_user_last_name: string; // Last name of the collection user
};

export type Trail = {
	id: string;
	user: string;
	name: string;
	location: string; // UUID of the location
	created_at: string; // ISO 8601 date string
	link?: string | null; // Optional link to the trail
	wanderer_id?: string | null; // Optional ID for integration with Wanderer
	provider: string; // Provider of the trail data, e.g., 'wanderer', 'external'
	wanderer_data: WandererTrail | null; // Optional data from Wanderer integration
	wanderer_link: string | null; // Optional link to the Wanderer trail
};

export type StravaActivity = {
	id: number;
	name: string;
	type: string;
	sport_type: string;
	distance: number;
	distance_km: number;
	distance_miles: number;
	moving_time: number;
	elapsed_time: number;
	rest_time: number;
	total_elevation_gain: number;
	estimated_elevation_loss: number;
	elev_high: number;
	elev_low: number;
	total_elevation_range: number;
	start_date: string; // ISO 8601 format
	start_date_local: string; // ISO 8601 format
	timezone: string;
	timezone_raw: string;
	average_speed: number;
	average_speed_kmh: number;
	average_speed_mph: number;
	max_speed: number;
	max_speed_kmh: number;
	max_speed_mph: number;
	pace_per_km_seconds: number;
	pace_per_mile_seconds: number;
	grade_adjusted_average_speed: number | null;
	average_cadence: number | null;
	average_watts: number | null;
	max_watts: number | null;
	kilojoules: number | null;
	calories: number | null;
	achievement_count: number;
	kudos_count: number;
	comment_count: number;
	pr_count: number;
	gear_id: string | null;
	device_name: string | null;
	trainer: boolean;
	manual: boolean;
	start_latlng: [number, number] | null; // [latitude, longitude]
	end_latlng: [number, number] | null; // [latitude, longitude]
	export_original: string; // URL
	export_gpx: string; // URL
	visibility: string;
	photo_count: number;
	has_heartrate: boolean;
	flagged: boolean;
	commute: boolean;
};

export type Activity = {
	id: string;
	user: string;
	visit: string;
	trail: string | null;
	gpx_file: string | null;
	geojson: any | undefined; // GeoJSON representation of the activity
	name: string;
	sport_type: string;
	distance: number | null;
	moving_time: string | null; // ISO 8601 duration string
	elapsed_time: string | null; // ISO 8601 duration string
	rest_time: string | null; // ISO 8601 duration string
	elevation_gain: number | null;
	elevation_loss: number | null;
	elev_high: number | null;
	elev_low: number | null;
	start_date: string | null; // ISO 8601 date string
	start_date_local: string | null; // ISO 8601 date string
	timezone: string | null;
	average_speed: number | null;
	max_speed: number | null;
	average_cadence: number | null;
	calories: number | null;
	start_lat: number | null;
	start_lng: number | null;
	end_lat: number | null;
	end_lng: number | null;
	external_service_id: string | null;
};

export type Visit = {
	id: string;
	start_date: string;
	end_date: string;
	notes: string;
	timezone: string | null;
	activities: Activity[];
	location: string;
	created_at: string;
	updated_at: string;
};

export type TransportationVisit = {
	id: string;
	start_date: string;
	end_date: string;
	notes: string;
	start_timezone: string;
	end_timezone: string;
	activities?: Activity[];
};

export type WandererTrail = {
	id: string;
	name: string;
	distance: number;
	duration: number;
	elevation_gain: number;
	elevation_loss: number;
	author: string;
	category: string;
	collectionId: string;
	collectionName: string;
	created: string; // ISO 8601 date string
	date: string;
	description: string;
	difficulty: string;
	external_id: string;
	external_provider: string;
	gpx: string;
	iri: string;
	lat: number;
	like_count: number;
	location: string;
	lon: number;
	photos: string[];
	public: boolean;
	tags: string[];
	thumbnail: number;
	updated: string; // ISO 8601 date string
	waypoints: string[];
};

export type Pin = {
	id: string;
	name: string;
	latitude: string;
	longitude: string;
	is_visited?: boolean;
	category: Category | null;
};
