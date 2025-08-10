<script lang="ts">
	import type { Trail } from '$lib/types';
	import { t } from 'svelte-i18n';

	// Icons (only those used)
	import Calendar from '~icons/mdi/calendar';
	import Camera from '~icons/mdi/camera';
	import Clock from '~icons/mdi/clock';
	import MapPin from '~icons/mdi/map-marker';
	import TrendingUp from '~icons/mdi/trending-up';
	import Users from '~icons/mdi/account-supervisor';

	export let trail: Trail;
	export let measurementSystem: 'metric' | 'imperial' = 'metric';

	function getDistance(meters: number) {
		return measurementSystem === 'imperial'
			? `${(meters * 0.000621371).toFixed(2)} mi`
			: `${(meters / 1000).toFixed(2)} km`;
	}

	function getElevation(meters: number) {
		return measurementSystem === 'imperial'
			? `${(meters * 3.28084).toFixed(1)} ft`
			: `${meters.toFixed(1)} m`;
	}

	function getDuration(minutes: number) {
		const hours = Math.floor(minutes / 60);
		const mins = minutes % 60;
		return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
	}

	function formatDate(date: string | number | Date) {
		return new Date(date).toLocaleDateString();
	}
</script>

<div class="card bg-base-100 shadow">
	<div class="card-body p-4">
		<div class="flex items-start justify-between">
			<div class="flex-1">
				<!-- Trail Name -->
				<h2 class="text-xl font-bold leading-tight mb-1">{trail.name}</h2>

				<!-- Provider + Created Date -->
				<div class="flex items-center gap-2 mb-2">
					{#if trail.provider}
						<span class="badge badge-outline badge-sm">{trail.provider}</span>
					{/if}
					<span class="text-sm opacity-70">
						{$t('adventures.created')}: {formatDate(trail.created_at)}
					</span>
				</div>

				{#if trail.wanderer_data}
					<div class="mb-4 space-y-3">
						<!-- Trail Stats -->
						<div class="grid grid-cols-2 gap-3">
							<div class="flex items-center gap-2 text-sm">
								<MapPin class="w-3 h-3 text-base-content/60" />
								<span class="text-base-content/80">
									{getDistance(trail.wanderer_data.distance)}
								</span>
							</div>

							{#if trail.wanderer_data.duration > 0}
								<div class="flex items-center gap-2 text-sm">
									<Clock class="w-3 h-3 text-base-content/60" />
									<span class="text-base-content/80">
										{getDuration(trail.wanderer_data.duration)}
									</span>
								</div>
							{/if}

							{#if trail.wanderer_data.elevation_gain > 0}
								<div class="flex items-center gap-2 text-sm">
									<TrendingUp class="w-3 h-3 text-base-content/60" />
									<span class="text-base-content/80">
										{getElevation(trail.wanderer_data.elevation_gain)}
										{$t('adventures.gain')}
									</span>
								</div>
							{/if}

							<div class="flex items-center gap-2 text-sm">
								<Calendar class="w-3 h-3 text-base-content/60" />
								<span class="text-base-content/80">
									{formatDate(trail.wanderer_data.date)}
								</span>
							</div>
						</div>

						<!-- Difficulty + Likes -->
						{#if trail.wanderer_data.difficulty}
							<div class="flex items-center gap-2">
								<span
									class="badge badge-sm"
									class:badge-success={trail.wanderer_data.difficulty === 'easy'}
									class:badge-warning={trail.wanderer_data.difficulty === 'moderate'}
									class:badge-error={trail.wanderer_data.difficulty === 'hard'}
								>
									{trail.wanderer_data.difficulty}
								</span>

								{#if trail.wanderer_data.like_count > 0}
									<div class="flex items-center gap-1 text-xs text-base-content/60">
										<Users class="w-3 h-3" />
										{$t('adventures.likes')}: {trail.wanderer_data.like_count}
									</div>
								{/if}
							</div>
						{/if}

						<!-- Description -->
						{#if trail.wanderer_data.description}
							<div class="text-sm text-base-content/70 leading-relaxed">
								{@html trail.wanderer_data.description}
							</div>
						{/if}

						<!-- Location -->
						{#if trail.wanderer_data.location}
							<div class="text-xs text-base-content/60 flex items-center gap-1">
								<MapPin class="w-3 h-3" />
								{trail.wanderer_data.location}
							</div>
						{/if}

						<!-- Photos -->
						{#if trail.wanderer_data.photos?.length > 0}
							<div class="flex items-center gap-1 text-xs text-base-content/60">
								<Camera class="w-3 h-3" />
								{$t('adventures.photos')}: {trail.wanderer_data.photos.length}
							</div>
						{/if}
					</div>
				{/if}
			</div>

			{#if trail.link || trail.wanderer_link}
				<a
					href={trail.wanderer_link || trail.link}
					target="_blank"
					rel="noopener noreferrer"
					class="btn btn-sm btn-primary"
				>
					🔗 {$t('adventures.view_trail')}
				</a>
			{/if}
		</div>
	</div>
</div>
