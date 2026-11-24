<script lang="ts">
	import { t } from 'svelte-i18n';
	import { percentage } from './format.js';
	import type { ProfileStatsData } from './types.js';

	import Flag from '~icons/mdi/flag-checkered-variant';
	import MapStar from '~icons/mdi/map-marker-star-outline';
	import City from '~icons/mdi/city-variant-outline';

	interface Props {
		stats: ProfileStatsData;
	}

	let { stats }: Props = $props();

	const rows = $derived([
		{
			icon: Flag,
			label: $t('profile.visited_countries'),
			suffix: $t('profile.of_world'),
			value: stats.visited_country_count,
			total: stats.total_countries,
			bar: 'progress-success',
			tone: 'text-success bg-success/10'
		},
		{
			icon: MapStar,
			label: $t('profile.visited_regions'),
			suffix: $t('profile.explored'),
			value: stats.visited_region_count,
			total: stats.total_regions,
			bar: 'progress-info',
			tone: 'text-info bg-info/10'
		},
		{
			icon: City,
			label: $t('profile.visited_cities'),
			suffix: $t('profile.discovered'),
			value: stats.visited_city_count,
			total: stats.total_cities,
			bar: 'progress-warning',
			tone: 'text-warning bg-warning/10'
		}
	]);
</script>

<div class="grid gap-4 md:grid-cols-3">
	{#each rows as row}
		<div class="card border border-base-300/60 bg-base-100 shadow-sm">
			<div class="card-body gap-3 p-5">
				<div class="flex items-center gap-3">
					<div class="rounded-lg p-2 {row.tone}">
						<row.icon class="h-5 w-5" />
					</div>
					<div class="text-sm font-medium text-base-content/70">{row.label}</div>
				</div>
				<div class="flex items-baseline gap-2">
					<span class="text-3xl font-bold">{row.value.toLocaleString()}</span>
					<span class="text-sm text-base-content/50">/ {row.total.toLocaleString()}</span>
				</div>
				<progress
					class="progress {row.bar} h-2 w-full"
					value={row.value}
					max={Math.max(row.total, 1)}
				></progress>
				<div class="text-xs text-base-content/60">
					{percentage(row.value, row.total)}% {row.suffix}
				</div>
			</div>
		</div>
	{/each}
</div>
