import type { Map as MapLibreMap } from 'maplibre-gl';
import type { ClusterOptions } from 'svelte-maplibre';

/**
 * MapLibre 4 scaled a cluster radius to tile units (x16) when a source was created, but stored a radius
 * changed through `setClusterOptions()` as-is. svelte-maplibre 0.9 always calls that on mount, so a
 * configured `radius: 300` actually clustered within 300 / 16 ~= 19px. MapLibre 6 interprets the radius
 * as real pixels, which made clusters swallow far more pins. Convert so the established density is kept.
 */
const LEGACY_RADIUS_DIVISOR = 16;

export function toMapLibreClusterOptions(
	options: ClusterOptions | undefined
): ClusterOptions | undefined {
	if (!options || options.radius === undefined) return options;
	return { ...options, radius: options.radius / LEGACY_RADIUS_DIVISOR };
}

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
