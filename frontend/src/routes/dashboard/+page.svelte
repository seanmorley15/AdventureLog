<script lang="ts">
	import AdventureCard from '$lib/components/AdventureCard.svelte';
	import type { PageData } from './$types';
	import { t } from 'svelte-i18n';

	export let data: PageData;

	import FlagCheckeredVariantIcon from '~icons/mdi/flag-checkered-variant';
	import Airplane from '~icons/mdi/airplane';
	import CityVariantOutline from '~icons/mdi/city-variant-outline';

	const user = data.user;
	const recentAdventures = data.props.adventures;
	const stats = data.props.stats;
</script>

<div class="container mx-auto p-4">
	<!-- Welcome Message -->
	<div class="mb-8">
		<h1 class="text-4xl font-extrabold">{$t('dashboard.welcome_back')}, {user?.first_name}!</h1>
	</div>

	<!-- Stats -->
	<div class="stats shadow mb-8 w-full bg-neutral">
		<div class="stat">
			<div class="stat-figure text-primary">
				<FlagCheckeredVariantIcon class="w-10 h-10 inline-block" />
			</div>
			<div class="stat-title text-neutral-content">{$t('dashboard.countries_visited')}</div>
			<div class="stat-value text-primary">{stats.country_count}</div>
		</div>
		<div class="stat">
			<div class="stat-figure text-secondary">
				<Airplane class="w-10 h-10 inline-block" />
			</div>
			<div class="stat-title text-neutral-content">{$t('dashboard.total_adventures')}</div>
			<div class="stat-value text-secondary">{stats.adventure_count}</div>
		</div>
		<div class="stat">
			<div class="stat-figure text-success">
				<CityVariantOutline class="w-10 h-10 inline-block" />
			</div>
			<div class="stat-title text-neutral-content">{$t('dashboard.total_visited_regions')}</div>
			<div class="stat-value text-success">{stats.visited_region_count}</div>
		</div>
	</div>

	<!-- Recent Adventures -->
	{#if recentAdventures.length > 0}
		<h2 class="text-3xl font-semibold mb-4">{$t('dashboard.recent_adventures')}</h2>
		<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
			{#each recentAdventures as adventure}
				<AdventureCard {adventure} user={data.user} readOnly />
			{/each}
		</div>
	{/if}

	<!-- Inspiration if there are no recent adventures -->
	{#if recentAdventures.length === 0}
		<div
			class="flex flex-col items-center justify-center bg-neutral shadow p-8 mb-8 rounded-lg text-neutral-content"
		>
			<h2 class="text-3xl font-semibold mb-4">{$t('dashboard.no_recent_adventures')}</h2>
			<p class="text-lg text-center">
				{$t('dashboard.add_some')}
			</p>
			<a href="/adventures" class="btn btn-primary mt-4">{$t('map.add_adventure')}</a>
		</div>
	{/if}
</div>

<svelte:head>
	<title>Dashboard | AdventureLog</title>
	<meta name="description" content="Home dashboard for AdventureLog." />
</svelte:head>
