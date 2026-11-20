export type ActivityRecord = {
	metric_key: string;
	metric_value: number;
	activity_id: string;
	activity_name: string | null;
	sport_type: string | null;
	start_date: string | null;
	location_id: string | null;
	location_name: string | null;
};

export type RecordHolders = {
	max_distance: ActivityRecord | null;
	max_speed: ActivityRecord | null;
	max_elevation_gain: ActivityRecord | null;
	max_calories: ActivityRecord | null;
};

export type ActivityCategoryStats = {
	count: number;
	total_distance: number;
	total_moving_time: number;
	total_elevation_gain: number;
	total_elevation_loss: number;
	avg_distance: number;
	max_distance: number;
	avg_elevation_gain: number;
	max_elevation_gain: number;
	avg_speed: number;
	max_speed: number;
	total_calories: number;
	record_holders: RecordHolders;
	sports: Record<string, { count: number; total_distance: number; total_elevation_gain: number }>;
};

export type ProfileStatsData = {
	visited_country_count: number;
	total_countries: number;
	visited_region_count: number;
	total_regions: number;
	visited_city_count: number;
	total_cities: number;
	trips_count: number;
	location_count: number;
	activities_overall: {
		total_count: number;
		total_distance: number;
		total_moving_time: number;
		total_elevation_gain: number;
		total_elevation_loss: number;
		total_calories: number;
		record_holders: RecordHolders;
	};
	activities_by_category: Record<string, ActivityCategoryStats>;
};

export type ProfilePin = {
	id: string;
	name: string;
	latitude: number;
	longitude: number;
	category: string | null;
	category_name: string | null;
	is_visited: boolean;
};

export type LocationsPage = {
	count: number;
	next: string | null;
	results: import('#lib/types.js').Location[];
};

export type LocationOrdering = 'recent' | 'oldest' | 'name' | 'rating';
