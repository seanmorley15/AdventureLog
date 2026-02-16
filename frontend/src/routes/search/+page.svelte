<script lang="ts">
	import LocationCard from '$lib/components/cards/LocationCard.svelte';
	import RegionCard from '$lib/components/cards/RegionCard.svelte';
	import CityCard from '$lib/components/cards/CityCard.svelte';
	import CountryCard from '$lib/components/cards/CountryCard.svelte';
	import CollectionCard from '$lib/components/cards/CollectionCard.svelte';
	import TransportationCard from '$lib/components/cards/TransportationCard.svelte';
	import LodgingCard from '$lib/components/cards/LodgingCard.svelte';
	import UserCard from '$lib/components/cards/UserCard.svelte';
	import { page } from '$app/stores';
	import type { PageData } from './$types';
	import { t } from 'svelte-i18n';
	import type {
		Location,
		Collection,
		Transportation,
		Lodging,
		User,
		Country,
		Region,
		City,
		VisitedRegion,
		VisitedCity
	} from '$lib/types';
	import SearchIcon from '~icons/mdi/magnify';
	import PlaneIcon from '~icons/mdi/airplane';
	import HotelIcon from '~icons/mdi/bed';

	export let data: PageData;

	// Whenever the query changes in the URL, SvelteKit automatically re-calls +page.server.ts
	// and updates 'data'. This reactive statement reads the updated 'query' from $page:
	$: query = $page.url.searchParams.get('query') ?? '';

	// Assign updated results from data, so when data changes, the displayed items update:
	$: locations = data.locations as Location[];
	$: collections = data.collections as Collection[];
	$: transportations = data.transportations as Transportation[];
	$: lodging = data.lodging as Lodging[];
	$: users = data.users as User[];
	$: countries = data.countries as Country[];
	$: regions = data.regions as Region[];
	$: cities = data.cities as City[];
	$: visited_regions = data.visited_regions as VisitedRegion[];
	$: visited_cities = data.visited_cities as VisitedCity[];

	// new stats
	$: totalResults =
		locations.length +
		collections.length +
		transportations.length +
		lodging.length +
		users.length +
		countries.length +
		regions.length +
		cities.length;
	$: hasResults = totalResults > 0;
</script>

<svelte:head>
	<title>Search: {query}</title>
	<meta name="description" content="AdventureLog global search results for {query}" />
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-base-200 via-base-100 to-base-200">
	<!-- Header -->
	<div class="sticky top-0 z-40 bg-base-100/80 backdrop-blur-lg border-b border-base-300">
		<div class="container mx-auto px-6 py-4 flex items-center">
			<div class="flex items-center gap-3">
				<div class="p-2 bg-primary/10 rounded-xl">
					<SearchIcon class="w-8 h-8 text-primary" />
				</div>
				<div>
					<h1
						class="text-3xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent"
					>
						{$t('navbar.search')}{query ? `: ${query}` : ''}
					</h1>
					{#if hasResults}
						<p class="text-sm text-base-content/60">
							{totalResults}
							{totalResults !== 1 ? $t('search.results') : $t('search.result')}
							{$t('search.found')}
						</p>
					{/if}
				</div>
			</div>
		</div>
	</div>

	<!-- Main content -->
	<div class="container mx-auto px-6 py-8">
		{#if !hasResults}
			<div class="flex flex-col items-center justify-center py-16">
				<div class="p-6 bg-base-200/50 rounded-2xl mb-6">
					<SearchIcon class="w-16 h-16 text-base-content/30" />
				</div>
				<h3 class="text-xl font-semibold text-base-content/70 mb-2">
					{$t('adventures.no_results')}
				</h3>
				<p class="text-base-content/50 text-center max-w-md">
					{$t('search.try_searching_desc')}
				</p>
			</div>
		{:else}
			{#if locations.length > 0}
				<div class="mb-12">
					<div class="flex items-center gap-3 mb-6">
						<div class="p-2 bg-primary/10 rounded-lg">
							<SearchIcon class="w-6 h-6 text-primary" />
						</div>
						<h2 class="text-2xl font-bold">{$t('locations.locations')}</h2>
						<div class="badge badge-primary">{locations.length}</div>
					</div>
					<div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
						{#each locations as adventure}
							<LocationCard {adventure} user={null} />
						{/each}
					</div>
				</div>
			{/if}

			{#if collections.length > 0}
				<div class="mb-12">
					<div class="flex items-center gap-3 mb-6">
						<div class="p-2 bg-secondary/10 rounded-lg">
							<!-- you can replace with a CollectionIcon -->
							<SearchIcon class="w-6 h-6 text-secondary" />
						</div>
						<h2 class="text-2xl font-bold">{$t('navbar.collections')}</h2>
						<div class="badge badge-secondary">{collections.length}</div>
					</div>
					<div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
						{#each collections as collection}
							<CollectionCard {collection} type="" user={null} />
						{/each}
					</div>
				</div>
			{/if}

			{#if transportations.length > 0}
				<div class="mb-12">
					<div class="flex items-center gap-3 mb-6">
						<div class="p-2 bg-amber-500/10 rounded-lg">
							<PlaneIcon class="w-6 h-6 text-amber-500" />
						</div>
						<h2 class="text-2xl font-bold">{$t('navbar.transportation')}</h2>
						<div class="badge badge-warning">{transportations.length}</div>
					</div>
					<div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
						{#each transportations as transportation}
							<TransportationCard {transportation} user={null} />
						{/each}
					</div>
				</div>
			{/if}

			{#if lodging.length > 0}
				<div class="mb-12">
					<div class="flex items-center gap-3 mb-6">
						<div class="p-2 bg-pink-500/10 rounded-lg">
							<HotelIcon class="w-6 h-6 text-pink-500" />
						</div>
						<h2 class="text-2xl font-bold">{$t('navbar.lodging')}</h2>
						<div class="badge badge-secondary">{lodging.length}</div>
					</div>
					<div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
						{#each lodging as lodgingItem}
							<LodgingCard lodging={lodgingItem} user={null} />
						{/each}
					</div>
				</div>
			{/if}

			{#if countries.length > 0}
				<div class="mb-12">
					<div class="flex items-center gap-3 mb-6">
						<div class="p-2 bg-accent/10 rounded-lg">
							<!-- you can replace with a GlobeIcon -->
							<SearchIcon class="w-6 h-6 text-accent" />
						</div>
						<h2 class="text-2xl font-bold">{$t('search.countries')}</h2>
						<div class="badge badge-accent">{countries.length}</div>
					</div>
					<div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
						{#each countries as country}
							<CountryCard {country} />
						{/each}
					</div>
				</div>
			{/if}

			{#if regions.length > 0}
				<div class="mb-12">
					<div class="flex items-center gap-3 mb-6">
						<div class="p-2 bg-info/10 rounded-lg">
							<!-- MapIcon -->
							<SearchIcon class="w-6 h-6 text-info" />
						</div>
						<h2 class="text-2xl font-bold">{$t('map.regions')}</h2>
						<div class="badge badge-info">{regions.length}</div>
					</div>
					<div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
						{#each regions as region}
							<RegionCard
								{region}
								visited={visited_regions.some((vr) => vr.region === region.id)}
							/>
						{/each}
					</div>
				</div>
			{/if}

			{#if cities.length > 0}
				<div class="mb-12">
					<div class="flex items-center gap-3 mb-6">
						<div class="p-2 bg-error/10 rounded-lg">
							<!-- CityIcon -->
							<SearchIcon class="w-6 h-6 text-error" />
						</div>
						<h2 class="text-2xl font-bold">{$t('search.cities')}</h2>
						<div class="badge badge-error">{cities.length}</div>
					</div>
					<div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
						{#each cities as city}
							<CityCard {city} visited={visited_cities.some((vc) => vc.city === city.id)} />
						{/each}
					</div>
				</div>
			{/if}

			{#if users.length > 0}
				<div class="mb-12">
					<div class="flex items-center gap-3 mb-6">
						<div class="p-2 bg-success/10 rounded-lg">
							<!-- UserIcon -->
							<SearchIcon class="w-6 h-6 text-success" />
						</div>
						<h2 class="text-2xl font-bold">{$t('navbar.users')}</h2>
						<div class="badge badge-success">{users.length}</div>
					</div>
					<div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
						{#each users as user}
							<UserCard {user} />
						{/each}
					</div>
				</div>
			{/if}
		{/if}
	</div>
</div>
