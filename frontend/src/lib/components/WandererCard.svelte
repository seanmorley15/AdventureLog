<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { t } from 'svelte-i18n';
	const dispatch = createEventDispatcher();
	import MountainIcon from '~icons/mdi/mountain';
	import MapPinIcon from '~icons/mdi/map-marker';
	import CalendarIcon from '~icons/mdi/calendar';
	import CameraIcon from '~icons/mdi/camera';
	import FileIcon from '~icons/mdi/file';
	import LinkIcon from '~icons/mdi/link-variant';
	import type { WandererTrail } from '$lib/types';

	export let trail: WandererTrail;

	// Helper functions
	/**
	 * @param {number} distanceInMeters
	 */
	function formatDistance(distanceInMeters: number) {
		const miles = (distanceInMeters * 0.000621371).toFixed(1);
		return `${miles} mi`;
	}

	/**
	 * @param {number} elevationInMeters
	 */
	function formatElevation(elevationInMeters: number) {
		const feet = Math.round(elevationInMeters * 3.28084);
		return `${feet}ft`;
	}

	/**
	 * @param {string} difficulty
	 */
	function getDifficultyBadgeClass(difficulty: string) {
		switch (difficulty?.toLowerCase()) {
			case 'easy':
				return 'badge-success';
			case 'moderate':
				return 'badge-warning';
			case 'difficult':
				return 'badge-error';
			default:
				return 'badge-outline';
		}
	}

	/**
	 * @param {string | number | Date} dateString
	 */
	function formatDate(dateString: string | number | Date) {
		if (!dateString) return '';
		return new Date(dateString).toLocaleDateString();
	}

	/**
	 * @param {string} html
	 */
	function stripHtml(html: string) {
		const doc = new DOMParser().parseFromString(html, 'text/html');
		return doc.body.textContent || '';
	}
</script>

<div class="bg-base-200/50 p-4 rounded-lg shadow-sm">
	<div class="flex items-start justify-between">
		<div class="flex-1 min-w-0">
			<!-- Header with trail name and difficulty -->
			<div class="flex items-center gap-2 mb-2">
				<MountainIcon class="w-4 h-4 text-primary flex-shrink-0" />
				<h5 class="font-semibold text-base truncate">{trail.name}</h5>
				<span class="badge {getDifficultyBadgeClass(trail.difficulty)} badge-sm">
					{trail.difficulty}
				</span>
			</div>

			<!-- Location -->
			{#if trail.location}
				<div class="flex items-center gap-1 mb-2">
					<MapPinIcon class="w-3 h-3 text-base-content/60" />
					<span class="text-sm text-base-content/70">{trail.location}</span>
				</div>
			{/if}

			<!-- Trail stats -->
			<div class="text-xs text-base-content/70 space-y-1">
				{#if trail.distance}
					<div class="flex items-center gap-4">
						<span>{$t('adventures.distance')}: {formatDistance(trail.distance)}</span>
						{#if trail.duration > 0}
							<span>{$t('adventures.duration')}: {Math.round(trail.duration / 60)} min</span>
						{/if}
					</div>
				{/if}

				{#if trail.elevation_gain > 0 || trail.elevation_loss > 0}
					<div class="flex items-center gap-4">
						{#if trail.elevation_gain > 0}
							<span class="text-success">↗ {formatElevation(trail.elevation_gain)}</span>
						{/if}
						{#if trail.elevation_loss > 0}
							<span class="text-error">↘ {formatElevation(trail.elevation_loss)}</span>
						{/if}
					</div>
				{/if}

				{#if trail.waypoints && trail.waypoints.length > 0}
					<div>
						Waypoints: {trail.waypoints.length}
					</div>
				{/if}

				{#if trail.created}
					<div class="flex items-center gap-1">
						<CalendarIcon class="w-3 h-3" />
						<span>{$t('adventures.created')}: {formatDate(trail.created)}</span>
					</div>
				{/if}

				{#if trail.photos && trail.photos.length > 0}
					<div class="flex items-center gap-1">
						<CameraIcon class="w-3 h-3" />
						<span>{$t('adventures.photos')}: {trail.photos.length}</span>
					</div>
				{/if}

				{#if trail.gpx}
					<div class="flex items-center gap-1">
						<FileIcon class="w-3 h-3" />
						<a href={trail.gpx} target="_blank" class="link link-primary text-xs">
							{$t('adventures.view_gpx')}
						</a>
					</div>
				{/if}
			</div>

			<!-- Description preview -->
			{#if trail.description}
				<div class="mt-3 pt-2 border-t border-base-300">
					<p class="text-xs text-base-content/60 line-clamp-2">
						{stripHtml(trail.description).substring(0, 150)}...
					</p>
				</div>
			{/if}
		</div>

		<!-- button to link trail to activity -->
		<div class="flex-shrink-0 ml-4">
			<button
				class="btn btn-primary btn-xs tooltip tooltip-top"
				on:click={() => dispatch('link', trail)}
				aria-label="Link Trail to Activity"
			>
				<LinkIcon class="w-3 h-3" />
			</button>
		</div>
	</div>
</div>

<style>
	.line-clamp-2 {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style>
