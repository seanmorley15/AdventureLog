export type MeasurementSystem = 'metric' | 'imperial';

export function formatDistance(meters: number, system: MeasurementSystem): string {
	return system === 'imperial'
		? `${(meters * 0.000621371).toFixed(1)} mi`
		: `${(meters / 1000).toFixed(1)} km`;
}

export function formatElevation(meters: number, system: MeasurementSystem): string {
	return system === 'imperial'
		? `${Math.round(meters * 3.28084).toLocaleString()} ft`
		: `${Math.round(meters).toLocaleString()} m`;
}

export function formatSpeed(metersPerSecond: number, system: MeasurementSystem): string {
	return system === 'imperial'
		? `${(metersPerSecond * 2.237).toFixed(1)} mph`
		: `${(metersPerSecond * 3.6).toFixed(1)} km/h`;
}

export function formatDuration(seconds: number): string {
	const hours = Math.floor(seconds / 3600);
	const minutes = Math.floor((seconds % 3600) / 60);
	return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
}

export function percentage(value: number, total: number): number {
	if (!total || total <= 0) return 0;
	return Math.min(100, Math.round((value / total) * 100));
}

/** The traveler rank for a number of public locations: the highest threshold reached. */
const RANKS: [number, string][] = [
	[100, 'legendary_explorer'],
	[75, 'world_wanderer'],
	[50, 'explorer_master'],
	[35, 'globetrotter'],
	[25, 'seasoned_traveler'],
	[15, 'adventure_seeker'],
	[10, 'trailblazer'],
	[5, 'journey_starter'],
	[1, 'travel_enthusiast']
];

export function rankKey(locationCount: number): string {
	return RANKS.find(([min]) => locationCount >= min)?.[1] ?? 'new_explorer';
}
