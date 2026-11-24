export type LngLat = [number, number];

const toRad = (deg: number) => (deg * Math.PI) / 180;
const toDeg = (rad: number) => (rad * 180) / Math.PI;

/**
 * Points along the great-circle between two places, which is the arc a flight draws on a
 * flat map. Longitudes are unwrapped so a route over the antimeridian stays one line
 * instead of streaking across the whole map.
 */
export function greatCircleArc(from: LngLat, to: LngLat, steps = 64): LngLat[] {
	const [lng1, lat1] = [toRad(from[0]), toRad(from[1])];
	const [lng2, lat2] = [toRad(to[0]), toRad(to[1])];

	const d =
		2 *
		Math.asin(
			Math.sqrt(
				Math.sin((lat2 - lat1) / 2) ** 2 +
					Math.cos(lat1) * Math.cos(lat2) * Math.sin((lng2 - lng1) / 2) ** 2
			)
		);
	// Same spot, or exactly opposite: there is no single arc to draw.
	if (!Number.isFinite(d) || d < 1e-9 || Math.abs(d - Math.PI) < 1e-9) return [from, to];

	const points: LngLat[] = [];
	let previousLng = from[0];
	for (let i = 0; i <= steps; i++) {
		const f = i / steps;
		const a = Math.sin((1 - f) * d) / Math.sin(d);
		const b = Math.sin(f * d) / Math.sin(d);
		const x = a * Math.cos(lat1) * Math.cos(lng1) + b * Math.cos(lat2) * Math.cos(lng2);
		const y = a * Math.cos(lat1) * Math.sin(lng1) + b * Math.cos(lat2) * Math.sin(lng2);
		const z = a * Math.sin(lat1) + b * Math.sin(lat2);
		let lng = toDeg(Math.atan2(y, x));
		const lat = toDeg(Math.atan2(z, Math.sqrt(x * x + y * y)));
		while (lng - previousLng > 180) lng -= 360;
		while (lng - previousLng < -180) lng += 360;
		previousLng = lng;
		points.push([lng, lat]);
	}
	return points;
}

/** A GeoJSON line for the route: a flight arcs, anything else is a straight sketch. */
export function routeLine(
	from: LngLat,
	to: LngLat,
	arc: boolean
): GeoJSON.Feature<GeoJSON.LineString> {
	return {
		type: 'Feature',
		properties: {},
		geometry: { type: 'LineString', coordinates: arc ? greatCircleArc(from, to) : [from, to] }
	};
}
