<script lang="ts">
	import { stopPropagation } from 'svelte/legacy';

	import ImageDisplayModal from '../ImageDisplayModal.svelte';
	import type { ContentImage } from '$lib/types';

	interface Props {
		geojson: any;
		name?: string;
		images?: ContentImage[];
		heightClass?: string;
	}

	let {
		geojson,
		name = '',
		images = [],
		heightClass = 'h-48'
	}: Props = $props();

	let showImageModal = $state(false);
	let modalInitialIndex = $state(0);



	function openImageModal(initialIndex: number = 0) {
		if (!sortedImages.length) return;
		modalInitialIndex = initialIndex;
		showImageModal = true;
	}

	function closeImageModal() {
		showImageModal = false;
	}

	type LonLat = [number, number];
	type NormalizedPoint = { x: number; y: number };

	function extractLineCoords(data: any): LonLat[] {
		if (!data || typeof data !== 'object') return [];

		if (data.type === 'FeatureCollection' && Array.isArray(data.features)) {
			return data.features.flatMap((feature: any) => extractLineCoords(feature));
		}

		if (data.type === 'Feature') {
			return extractLineCoords(data.geometry);
		}

		if (data.type === 'GeometryCollection' && Array.isArray(data.geometries)) {
			return data.geometries.flatMap((geom: any) => extractLineCoords(geom));
		}

		if (data.type === 'LineString' && Array.isArray(data.coordinates)) {
			return sanitizeCoordinates(data.coordinates);
		}

		if (data.type === 'MultiLineString' && Array.isArray(data.coordinates)) {
			return data.coordinates.flatMap((line: any) => sanitizeCoordinates(line));
		}

		return [];
	}

	function sanitizeCoordinates(raw: any): LonLat[] {
		if (!Array.isArray(raw)) return [];
		const coords: LonLat[] = [];
		for (const point of raw) {
			if (!Array.isArray(point) || point.length < 2) continue;
			const lon = Number(point[0]);
			const lat = Number(point[1]);
			if (Number.isFinite(lon) && Number.isFinite(lat)) {
				coords.push([lon, lat]);
			}
		}
		return coords;
	}

	function normalizeCoords(coords: LonLat[]): NormalizedPoint[] {
		if (!coords.length) return [];

		const lons = coords.map(([lon]) => lon);
		const lats = coords.map(([, lat]) => lat);
		const minLon = Math.min(...lons);
		const maxLon = Math.max(...lons);
		const minLat = Math.min(...lats);
		const maxLat = Math.max(...lats);

		const spanLon = maxLon - minLon || 1;
		const spanLat = maxLat - minLat || 1;
		const padLon = spanLon * 0.05;
		const padLat = spanLat * 0.05;

		const originLon = minLon - padLon;
		const originLat = minLat - padLat;
		const scaleX = 100 / (spanLon + padLon * 2);
		const scaleY = 100 / (spanLat + padLat * 2);

		return coords.map(([lon, lat]) => ({
			x: (lon - originLon) * scaleX,
			y: 100 - (lat - originLat) * scaleY
		}));
	}

	function buildPath(points: NormalizedPoint[]): string {
		if (!points.length) return '';
		return points
			.map((p, idx) => `${idx === 0 ? 'M' : 'L'} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`)
			.join(' ');
	}
	let sortedImages = $derived([...images]
		.filter((img) => !!img?.image)
		.sort((a, b) => Number(b?.is_primary) - Number(a?.is_primary)));
	let routeCoordinates = $derived(extractLineCoords(geojson));
	let normalizedRoute = $derived(normalizeCoords(routeCoordinates));
	let pathD = $derived(buildPath(normalizedRoute));
	let hasRoute = $derived(!!pathD);
	let startPoint = $derived(normalizedRoute.length > 0 ? normalizedRoute[0] : null);
	let endPoint =
		$derived(normalizedRoute.length > 1 ? normalizedRoute[normalizedRoute.length - 1] : startPoint);
</script>

{#if showImageModal && sortedImages.length > 0}
	<ImageDisplayModal
		images={sortedImages}
		initialIndex={modalInitialIndex}
		on:close={closeImageModal}
		{name}
	/>
{/if}

<div
	class={`relative w-full ${heightClass} rounded-t-2xl bg-gradient-to-r from-success via-base to-primary overflow-hidden`}
	aria-label="route-preview"
>
	<svg viewBox="0 0 100 100" class="w-full h-full" role="img" aria-label="Route preview">
		<!-- No separate bg; rely on parent gradient -->

		{#if hasRoute}
			<g stroke-linecap="round" stroke-linejoin="round">
				<path
					d={pathD}
					fill="none"
					stroke="var(--color-base-content, #111827)"
					stroke-width="2.6"
					opacity="0.55"
				/>
				{#if startPoint}
					<circle
						cx={startPoint.x}
						cy={startPoint.y}
						r="2.4"
						fill="var(--color-base-content, #111827)"
						opacity="0.9"
					/>
				{/if}
				{#if endPoint}
					<circle
						cx={endPoint.x}
						cy={endPoint.y}
						r="2.8"
						fill="var(--color-base-content, #111827)"
						opacity="0.9"
					/>
				{/if}
			</g>
		{:else}
			<text
				x="50"
				y="50"
				text-anchor="middle"
				fill="var(--color-base-content, #111827)"
				opacity="0.6"
			>
				Route unavailable
			</text>
		{/if}
	</svg>

	<div class="absolute top-3 left-3 badge badge-primary gap-1 shadow-sm">
		<span class="text-xs font-semibold">GPX</span>
		<span class="text-xs">Route</span>
	</div>

	{#if sortedImages.length > 0}
		<button
			type="button"
			onclick={stopPropagation(() => openImageModal(0))}
			class="btn btn-xs btn-neutral absolute bottom-3 right-3 shadow-sm"
		>
			View photos ({sortedImages.length})
		</button>
	{/if}
</div>
