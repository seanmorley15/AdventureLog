type MapWithViewport = {
	getCanvas: () => { clientWidth: number; clientHeight: number };
	unproject: (point: [number, number]) => { lng: number; lat: number };
	on: (type: string, listener: () => void) => void;
	off: (type: string, listener: () => void) => void;
};

/** Geographic point at the center pixel of the map container (visual viewport center). */
export function getMapViewportCenter(map: MapWithViewport): { lng: number; lat: number } {
	const canvas = map.getCanvas();
	const lngLat = map.unproject([canvas.clientWidth / 2, canvas.clientHeight / 2]);
	return { lng: lngLat.lng, lat: lngLat.lat };
}

export function bindMapViewportCenterSync(
	map: MapWithViewport,
	onCenter: (center: { lng: number; lat: number }) => void
): () => void {
	const sync = () => onCenter(getMapViewportCenter(map));
	map.on('move', sync);
	map.on('zoom', sync);
	map.on('resize', sync);
	map.on('moveend', sync);
	sync();
	return () => {
		map.off('move', sync);
		map.off('zoom', sync);
		map.off('resize', sync);
		map.off('moveend', sync);
	};
}
