<script lang="ts">
	import { stopPropagation } from 'svelte/legacy';

	import { createEventDispatcher } from 'svelte';
	import { t } from 'svelte-i18n';
	import { Marker } from 'svelte-maplibre';
	import type { Recommendation } from '$lib/types';
	import { osmTagToEmoji } from '$lib';

	interface Props {
		recommendations?: Recommendation[];
		selectedId?: string | null;
	}

	let { recommendations = [], selectedId = null }: Props = $props();

	const dispatch = createEventDispatcher<{
		select: { item: Recommendation };
	}>();

	let hoveredId: string | null = $state(null);

	function normalizeTag(tag: string): string {
		return tag.trim().toLowerCase().replace(/-/g, '_').replace(/\s+/g, '_');
	}

	function recommendationEmoji(rec: Recommendation): string {
		const raw = rec.primary_type || rec.types?.[0] || '';
		if (!raw) return '📍';
		return osmTagToEmoji(normalizeTag(raw));
	}

	function recMarkerClass(rec: Recommendation, isSelected: boolean, isHovered: boolean): string {
		const base =
			'map-rec-hit grid place-items-center w-8 h-8 rounded-full border-2 border-white shadow-md text-base cursor-pointer transition-transform';
		if (isSelected) return `${base} scale-110 ring-2 ring-warning ring-offset-1 bg-warning/90`;
		if (isHovered) return `${base} scale-110 bg-accent hover:bg-accent`;
		return `${base} bg-accent/90 hover:bg-accent hover:scale-105`;
	}

	function formatDistance(km: number): string {
		if (km < 1) return `${Math.round(km * 1000)} m`;
		return `${km.toFixed(km < 10 ? 1 : 0)} km`;
	}
</script>

{#each recommendations as rec (rec.id)}
	{#if rec.latitude != null && rec.longitude != null}
		{@const isSelected = selectedId === rec.id}
		{@const isHovered = hoveredId === rec.id}
		{@const isRaised = isHovered || isSelected}
		<Marker
			lngLat={[rec.longitude, rec.latitude]}
			class="map-rec-marker {isRaised ? 'map-rec-marker-raised' : ''}"
		>
			<div class="relative group">
				<button
					type="button"
					class={recMarkerClass(rec, isSelected, isHovered)}
					aria-label={rec.name}
					onmouseenter={() => (hoveredId = rec.id)}
					onmouseleave={() => {
						if (!isSelected) hoveredId = null;
					}}
					onfocus={() => (hoveredId = rec.id)}
					onblur={() => {
						if (!isSelected) hoveredId = null;
					}}
					onclick={stopPropagation(() => dispatch('select', { item: rec }))}
				>
					{recommendationEmoji(rec)}
				</button>

				<div
					class="map-rec-popup absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 pointer-events-none group-hover:opacity-100 group-focus-within:opacity-100 transition-all duration-200"
					class:opacity-100={isRaised}
				>
					<div
						class="card card-compact bg-base-100 shadow-xl border border-base-300 min-w-48 max-w-72"
					>
						<div class="card-body gap-2 p-3">
							<h3 class="font-semibold text-sm leading-tight">{rec.name}</h3>
							{#if rec.address}
								<p class="text-xs text-base-content/70 line-clamp-2">{rec.address}</p>
							{/if}
							<div class="flex flex-wrap items-center gap-1.5">
								{#if rec.rating != null}
									<span class="badge badge-sm badge-warning">{rec.rating.toFixed(1)} ★</span>
								{/if}
								{#if rec.distance_km != null}
									<span class="badge badge-ghost badge-sm">{formatDistance(rec.distance_km)}</span>
								{/if}
							</div>
							<p class="text-xs text-base-content/60">{$t('map.view_details')}</p>
						</div>
					</div>
				</div>
			</div>
		</Marker>
	{/if}
{/each}

<style>
	:global(.maplibregl-marker.map-rec-marker),
	:global(.mapboxgl-marker.map-rec-marker) {
		pointer-events: none;
		z-index: 1;
	}

	:global(.maplibregl-marker.map-rec-marker-raised),
	:global(.mapboxgl-marker.map-rec-marker-raised) {
		z-index: 100000 !important;
	}

	:global(.maplibregl-marker.map-rec-marker .map-rec-hit),
	:global(.mapboxgl-marker.map-rec-marker .map-rec-hit) {
		pointer-events: auto;
	}

	:global(.maplibregl-marker.map-rec-marker .map-rec-popup),
	:global(.mapboxgl-marker.map-rec-marker .map-rec-popup) {
		z-index: 100001;
	}
</style>
