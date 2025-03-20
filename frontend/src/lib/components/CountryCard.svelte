<script lang="ts">
	import { goto } from '$app/navigation';
	import type { Country } from '$lib/types';
	import { t, locale } from 'svelte-i18n';

	import MapMarkerStar from '~icons/mdi/map-marker-star';

	export let country: Country;

	// Country name in the current locale
	let country_name_locale = country.name;

	// Subscribe to locale changes
	locale.subscribe((lang) => {
		country_name_locale = get_country_name(lang);
	});

	/**
	 * Get the country name in the current locale
	 * @param lang - The current locale
	 * @returns The country name in the current locale
	 */
	function get_country_name(lang: string | null | undefined) {
		if (!lang) {
			return country.name;
		}
		const translations = country.translations;
		if (translations[lang]) {
			return translations[lang];
		}
		for (const [key, value] of Object.entries(translations)) {
			if (key.toLowerCase().includes(lang.toLowerCase())) {
				return value;
			}
		}
		return country.name;
	}

	async function nav() {
		goto(`/worldtravel/${country.country_code}`);
	}
</script>

<div
	class="card w-full max-w-xs sm:max-w-sm md:max-w-md lg:max-w-md xl:max-w-md bg-neutral text-neutral-content shadow-xl overflow-hidden"
>
	<figure>
		<!-- svelte-ignore a11y-img-redundant-alt -->
		<img src={country.flag_url} alt="No image available" class="w-full h-48 object-cover" />
	</figure>
	<div class="card-body">
		<h2 class="card-title overflow-ellipsis">{country_name_locale}</h2>
		<div class="flex flex-wrap gap-2">
			{#if country.subregion}
				<div class="badge badge-primary">{country.subregion}</div>
			{/if}
			{#if country.capital}
				<div class="badge badge-secondary">
					<MapMarkerStar class="-ml-1 mr-1" />{country.capital}
				</div>
			{/if}
			{#if country.num_visits > 0 && country.num_visits != country.num_regions}
				<div class="badge badge-accent">
					Visited {country.num_visits} Region{country.num_visits > 1 ? 's' : ''}
				</div>
			{:else if country.num_visits > 0 && country.num_visits === country.num_regions}
				<div class="badge badge-success">{$t('adventures.visited')}</div>
			{:else}
				<div class="badge badge-error">{$t('adventures.not_visited')}</div>
			{/if}
		</div>

		<div class="card-actions justify-end">
			<!-- <button class="btn btn-info" on:click={moreInfo}>More Info</button> -->
			<button class="btn btn-primary" on:click={nav}>{$t('notes.open')}</button>
		</div>
	</div>
</div>
