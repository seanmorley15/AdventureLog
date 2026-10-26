import * as maplibregl from 'maplibre-gl';
// MapLibre 6 is ESM-only and cannot locate its worker on its own under Vite.
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';

let configured = false;

/** Point MapLibre at its bundled worker. Safe to call repeatedly; no-op during SSR. */
export function configureMapLibreWorker() {
	if (configured || typeof window === 'undefined') return;
	maplibregl.setWorkerUrl(workerUrl);
	configured = true;
}
