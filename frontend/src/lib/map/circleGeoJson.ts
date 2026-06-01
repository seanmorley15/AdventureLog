type CircleFeature = {
	type: 'Feature';
	geometry: { type: 'Polygon'; coordinates: [number, number][][] };
	properties: Record<string, never>;
};

export function circlePolygon(lng: number, lat: number, radiusMeters: number, steps = 64): CircleFeature {
	const coordinates: [number, number][] = [];
	const latRad = (lat * Math.PI) / 180;
	const metersPerDegLat = 110540;
	const metersPerDegLng = Math.max(111320 * Math.cos(latRad), 1);

	for (let i = 0; i <= steps; i++) {
		const angle = (i / steps) * 2 * Math.PI;
		const dx = (radiusMeters / metersPerDegLng) * Math.cos(angle);
		const dy = (radiusMeters / metersPerDegLat) * Math.sin(angle);
		coordinates.push([lng + dx, lat + dy]);
	}

	return {
		type: 'Feature',
		geometry: {
			type: 'Polygon',
			coordinates: [coordinates]
		},
		properties: {}
	};
}

export function circleFeatureCollection(lng: number, lat: number, radiusMeters: number) {
	return {
		type: 'FeatureCollection' as const,
		features: [circlePolygon(lng, lat, radiusMeters)]
	};
}
