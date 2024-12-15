<script lang="ts">
	import AdventureCard from '$lib/components/AdventureCard.svelte';
	import type { PageData } from './$types';
	import { t } from 'svelte-i18n';

	export let data: PageData;

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
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					class="inline-block w-8 h-8 stroke-current"
					><path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
					></path></svg
				>
			</div>
			<div class="stat-title text-neutral-content">{$t('dashboard.countries_visited')}</div>
			<div class="stat-value text-primary">{stats.country_count}</div>
		</div>
		<div class="stat">
			<div class="stat-figure text-secondary">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					class="inline-block w-8 h-8 stroke-current"
					><path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
					></path></svg
				>
			</div>
			<div class="stat-title text-neutral-content">{$t('dashboard.total_adventures')}</div>
			<div class="stat-value text-secondary">{stats.adventure_count}</div>
		</div>
		<div class="stat">
			<div class="stat-figure text-success">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					class="inline-block w-8 h-8 stroke-current"
					><path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"
					></path></svg
				>
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
		<div class="flex flex-col items-center justify-center bg-neutral shadow p-8 mb-8 rounded-lg">
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
