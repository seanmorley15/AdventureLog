<script lang="ts">
	import { goto } from '$app/navigation';
	import type { Country } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	import { t } from 'svelte-i18n';

	import MapMarkerStar from '~icons/mdi/map-marker-star';
	import Launch from '~icons/mdi/launch';

	export let country: Country;

	async function nav() {
		goto(`/worldtravel/${country.country_code}`);
	}
</script>

<div
	class="card w-full max-w-md bg-base-300 text-base-content shadow-2xl hover:shadow-3xl transition-all duration-300 border border-base-300 hover:border-primary/20 group overflow-hidden"
>
	<!-- Flag Image -->
	<figure>
		<img src={country.flag_url} alt={`Flag of ${country.name}`} class="w-full h-48 object-cover" />
	</figure>

	<!-- Content -->
	<div class="card-body p-6 space-y-4">
		<!-- Title -->
		<a
			href="/worldtravel/{country.country_code}"
			class="text-xl font-bold text-left hover:text-primary transition-colors duration-200 line-clamp-2 group-hover:underline block"
		>
			{country.name}
		</a>

		<!-- Info Badges -->
		<div class="flex flex-wrap gap-2">
			{#if country.subregion}
				<div class="badge badge-primary">{country.subregion}</div>
			{/if}
			{#if country.capital}
				<div class="badge badge-secondary inline-flex items-center gap-1">
					<MapMarkerStar class="w-4 h-4" />
					{country.capital}
				</div>
			{/if}

			{#if country.num_visits > 0 && country.num_visits !== country.num_regions}
				<div class="badge badge-accent">
					Visited {country.num_visits} Region{country.num_visits > 1 ? 's' : ''}
				</div>
			{:else if country.num_visits > 0 && country.num_visits === country.num_regions}
				<div class="badge badge-success">{$t('adventures.visited')}</div>
			{:else}
				<div class="badge badge-error">{$t('adventures.not_visited')}</div>
			{/if}
		</div>

		<!-- Actions -->
		<div class="pt-4 border-t border-base-300 flex justify-end">
			<button class="btn btn-primary btn-sm flex items-center gap-1" on:click={nav}>
				<Launch class="w-4 h-4" />
				{$t('notes.open')}
			</button>
		</div>
	</div>
</div>

<style>
	.truncate {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
</style>
