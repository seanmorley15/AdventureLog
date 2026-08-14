<script lang="ts">
	import { goto } from '$app/navigation';
	import type { Country } from '$lib/types';
	import { t } from 'svelte-i18n';

	import MapMarkerStar from '~icons/mdi/map-marker-star';
	import ChevronRight from '~icons/mdi/chevron-right';
	import Check from '~icons/mdi/check-circle';
	import ProgressIcon from '~icons/mdi/progress-check';

	interface Props {
		country: Country;
	}

	let { country }: Props = $props();

	let visitStatus =
		$derived(country.num_visits === 0
			? 'none'
			: country.num_visits >= country.num_regions
				? 'complete'
				: 'partial');
	let progressPct =
		$derived(country.num_regions > 0 ? Math.round((country.num_visits / country.num_regions) * 100) : 0);

	function nav() {
		goto(`/worldtravel/${country.country_code}`);
	}
</script>

<button
	type="button"
	class="w-full grid items-center gap-4 px-4 py-3 text-left hover:bg-base-200/60 active:bg-base-200 transition-colors group country-row"
	onclick={nav}
>
	<img
		src={country.flag_url}
		alt=""
		class="w-12 h-8 object-cover rounded shadow-sm border border-base-300/50"
		loading="lazy"
	/>

	<div class="min-w-0">
		<span class="font-semibold truncate block group-hover:text-primary transition-colors">
			{country.name}
		</span>
		<span class="text-sm text-base-content/50 font-mono sm:hidden">{country.country_code}</span>
	</div>

	<span class="hidden md:block text-sm text-base-content/60 truncate">
		{country.subregion ?? '—'}
	</span>

	<span class="hidden md:inline-flex items-center gap-1.5 text-sm text-base-content/60 truncate">
		{#if country.capital}
			<MapMarkerStar class="w-4 h-4 shrink-0 opacity-60" />
			{country.capital}
		{:else}
			—
		{/if}
	</span>

	<div class="hidden sm:flex items-center gap-2">
		<progress
			class="progress progress-primary progress-sm flex-1 min-w-0"
			value={country.num_visits}
			max={country.num_regions || 1}
		></progress>
		<span class="text-sm tabular-nums text-base-content/60 shrink-0">
			{country.num_visits}/{country.num_regions}
		</span>
	</div>

	<div>
		{#if visitStatus === 'complete'}
			<span class="badge badge-success badge-sm gap-1">
				<Check class="w-3.5 h-3.5" />
				<span class="hidden lg:inline">{$t('adventures.visited')}</span>
			</span>
		{:else if visitStatus === 'partial'}
			<span class="badge badge-warning badge-sm gap-1">
				<ProgressIcon class="w-3.5 h-3.5" />
				{progressPct}%
			</span>
		{:else}
			<span class="badge badge-ghost badge-sm">{$t('adventures.not_visited')}</span>
		{/if}
	</div>

	<ChevronRight class="w-5 h-5 text-base-content/30 group-hover:text-primary" />
</button>

<style>
	.country-row {
		grid-template-columns: 3rem 1fr 9rem 8rem 8rem 6rem 1.5rem;
	}

	@media (max-width: 768px) {
		.country-row {
			grid-template-columns: 3rem 1fr auto 1.5rem;
		}
	}
</style>
