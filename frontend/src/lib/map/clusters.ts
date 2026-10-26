import type { Map as MapLibreMap } from 'maplibre-gl';

type ClusterSource = {
	getClusterExpansionZoom: (clusterId: number) => Promise<number>;
};

/**
 * Zoom the map in far enough for a cluster to split into its children.
 *
 * `getClusterExpansionZoom` is promise-based. After the eased zoom the new zoom level's tiles can
 * arrive after the final `moveend`, and svelte-maplibre's MarkerLayer only re-queries on movement,
 * so markers from the previous zoom would linger. Nudge it once the map is idle.
 */
export async function expandCluster(
	map: MapLibreMap,
	source: string,
	clusterId: number | string,
	center: [number, number]
): Promise<void> {
	const geoJsonSource = map.getSource(source) as unknown as ClusterSource | undefined;
	if (!geoJsonSource || typeof geoJsonSource.getClusterExpansionZoom !== 'function') return;

	const zoom = await geoJsonSource.getClusterExpansionZoom(Number(clusterId));
	map.easeTo({ center, zoom });
	map.once('idle', () => map.fire('moveend'));
}
