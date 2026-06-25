type MapWithViewport = {
	getCanvas: () => { clientWidth: number; clientHeight: number };
	getContainer?: () => HTMLElement;
	unproject: (point: [number, number]) => { lng: number; lat: number };
	getCenter?: () => { lng: number; lat: number };
	on: (type: string, listener: () => void) => void;
	off: (type: string, listener: () => void) => void;
};

/** Geographic point at the center pixel of the visible map viewport. */
export function getMapViewportCenter(
	map: MapWithViewport,
	viewportEl?: HTMLElement | null
): { lng: number; lat: number } {
	const container = map.getContainer?.() ?? map.getCanvas();
	if (!container) {
		const center = map.getCenter?.();
		if (center && Number.isFinite(center.lng) && Number.isFinite(center.lat)) {
			return { lng: center.lng, lat: center.lat };
		}
		return { lng: 0, lat: 0 };
	}

	if (viewportEl && map.getContainer) {
		const mapContainer = map.getContainer();
		const viewportRect = viewportEl.getBoundingClientRect();
		const mapRect = mapContainer.getBoundingClientRect();

		if (
			viewportRect.width > 0 &&
			viewportRect.height > 0 &&
			mapRect.width > 0 &&
			mapRect.height > 0
		) {
			const x = viewportRect.left + viewportRect.width / 2 - mapRect.left;
			const y = viewportRect.top + viewportRect.height / 2 - mapRect.top;
			const lngLat = map.unproject([x, y]);
			if (Number.isFinite(lngLat.lng) && Number.isFinite(lngLat.lat)) {
				return { lng: lngLat.lng, lat: lngLat.lat };
			}
		}
	}

	const width = container.clientWidth;
	const height = container.clientHeight;
	if (width > 0 && height > 0) {
		const lngLat = map.unproject([width / 2, height / 2]);
		if (Number.isFinite(lngLat.lng) && Number.isFinite(lngLat.lat)) {
			return { lng: lngLat.lng, lat: lngLat.lat };
		}
	}

	const center = map.getCenter?.();
	if (center && Number.isFinite(center.lng) && Number.isFinite(center.lat)) {
		return { lng: center.lng, lat: center.lat };
	}

	return { lng: 0, lat: 0 };
}

export function bindMapViewportCenterSync(
	map: MapWithViewport,
	onCenter: (center: { lng: number; lat: number }) => void,
	viewportEl?: HTMLElement | null
): () => void {
	const sync = () => onCenter(getMapViewportCenter(map, viewportEl));
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
