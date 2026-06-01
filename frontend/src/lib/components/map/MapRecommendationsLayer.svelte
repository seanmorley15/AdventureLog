<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { Marker } from 'svelte-maplibre';
	import type { Recommendation } from '$lib/types';
	import { osmTagToEmoji } from '$lib';

	export let recommendations: Recommendation[] = [];
	export let selectedId: string | null = null;

	const dispatch = createEventDispatcher<{
		select: { item: Recommendation };
	}>();

	function normalizeTag(tag: string): string {
		return tag
			.trim()
			.toLowerCase()
			.replace(/-/g, '_')
			.replace(/\s+/g, '_');
	}

	function recommendationEmoji(rec: Recommendation): string {
		const raw = rec.primary_type || rec.types?.[0] || '';
		if (!raw) return '📍';
		return osmTagToEmoji(normalizeTag(raw));
	}

	function recMarkerClass(rec: Recommendation, isSelected: boolean): string {
		const base =
			'grid place-items-center w-8 h-8 rounded-full border-2 border-white shadow-md text-base cursor-pointer transition-transform';
		if (isSelected) return `${base} scale-110 ring-2 ring-warning ring-offset-1 bg-warning/90`;
		return `${base} bg-accent/90 hover:bg-accent hover:scale-105`;
	}
</script>

{#each recommendations as rec (rec.id)}
	{#if rec.latitude != null && rec.longitude != null}
		<Marker lngLat={[rec.longitude, rec.latitude]} class="map-rec-marker">
			<button
				type="button"
				class={recMarkerClass(rec, selectedId === rec.id)}
				aria-label={rec.name}
				on:click|stopPropagation={() => dispatch('select', { item: rec })}
			>
				{recommendationEmoji(rec)}
			</button>
		</Marker>
	{/if}
{/each}

<style>
	:global(.maplibregl-marker.map-rec-marker),
	:global(.mapboxgl-marker.map-rec-marker) {
		pointer-events: none;
	}

	:global(.maplibregl-marker.map-rec-marker button),
	:global(.mapboxgl-marker.map-rec-marker button) {
		pointer-events: auto;
	}
</style>
