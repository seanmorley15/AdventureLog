<script lang="ts">
	export let data;
	import AdventureCard from '$lib/components/AdventureCard.svelte';
	import CollectionCard from '$lib/components/CollectionCard.svelte';
	import type { Adventure, Collection, User } from '$lib/types.js';
	import { t } from 'svelte-i18n';

	let stats: {
		visited_country_count: number;
		total_regions: number;
		trips_count: number;
		adventure_count: number;
		visited_region_count: number;
		total_countries: number;
		visited_city_count: number;
		total_cities: number;
	} | null;

	const user: User = data.user;
	const adventures: Adventure[] = data.adventures;
	const collections: Collection[] = data.collections;
	stats = data.stats || null;
</script>

<section class="min-h-screen bg-base-100 py-8 px-4">
	<div class="flex flex-col items-center">
		<!-- Profile Picture -->
		{#if user.profile_pic}
			<div class="avatar">
				<div
					class="w-24 rounded-full ring ring-primary ring-offset-base-100 ring-offset-2 shadow-md"
				>
					<img src={user.profile_pic} alt="Profile" />
				</div>
			</div>
		{:else}
			<!-- show first last initial -->
			<div class="avatar">
				<div
					class="w-24 rounded-full ring ring-primary ring-offset-base-100 ring-offset-2 shadow-md"
				>
					{#if user.first_name && user.last_name}
						<img
							src={`https://eu.ui-avatars.com/api/?name=${user.first_name}+${user.last_name}&size=250`}
							alt="Profile"
						/>
					{:else}
						<img
							src={`https://eu.ui-avatars.com/api/?name=${user.username}&size=250`}
							alt="Profile"
						/>
					{/if}
				</div>
			</div>
		{/if}

		<!-- User Name -->
		{#if user && user.first_name && user.last_name}
			<h1 class="text-4xl font-bold text-primary mt-4">
				{user.first_name}
				{user.last_name}
			</h1>
		{/if}
		<p class="text-lg text-base-content mt-2">{user.username}</p>

		<!-- Member Since -->
		{#if user && user.date_joined}
			<div class="mt-4 flex items-center text-center text-base-content">
				<p class="text-lg font-medium">{$t('profile.member_since')}</p>
				<div class="flex items-center ml-2">
					<iconify-icon icon="mdi:calendar" class="text-2xl text-primary"></iconify-icon>
					<p class="ml-2 text-lg">
						{new Date(user.date_joined).toLocaleDateString(undefined, { timeZone: 'UTC' })}
					</p>
				</div>
			</div>
		{/if}
	</div>

	<!-- Stats Section -->
	{#if stats}
		<div class="divider my-8"></div>

		<h2 class="text-2xl font-bold text-center mb-6 text-primary">
			{$t('profile.user_stats')}
		</h2>

		<div class="flex justify-center">
			<div class="stats stats-vertical lg:stats-horizontal shadow bg-base-200">
				<div class="stat">
					<div class="stat-title">{$t('navbar.adventures')}</div>
					<div class="stat-value text-center">{stats.adventure_count}</div>
				</div>

				<div class="stat">
					<div class="stat-title">{$t('navbar.collections')}</div>
					<div class="stat-value text-center">{stats.trips_count}</div>
				</div>

				<div class="stat">
					<div class="stat-title">{$t('profile.visited_countries')}</div>
					<div class="stat-value text-center">
						{stats.visited_country_count}
					</div>
					<div class="stat-desc text-center">
						{Math.round((stats.visited_country_count / stats.total_countries) * 100)}% {$t(
							'adventures.of'
						)}
						{stats.total_countries}
					</div>
				</div>

				<div class="stat">
					<div class="stat-title">{$t('profile.visited_regions')}</div>
					<div class="stat-value text-center">
						{stats.visited_region_count}
					</div>
					<div class="stat-desc text-center">
						{Math.round((stats.visited_region_count / stats.total_regions) * 100)}% {$t(
							'adventures.of'
						)}
						{stats.total_regions}
					</div>
				</div>

				<div class="stat">
					<div class="stat-title">{$t('profile.visited_cities')}</div>
					<div class="stat-value text-center">
						{stats.visited_city_count}
					</div>
					<div class="stat-desc text-center">
						{Math.round((stats.visited_city_count / stats.total_cities) * 100)}% {$t(
							'adventures.of'
						)}
						{stats.total_cities}
					</div>
				</div>
			</div>
		</div>
	{/if}

	<!-- Adventures Section -->
	<div class="divider my-8"></div>

	<h2 class="text-2xl font-bold text-center mb-6 text-primary">
		{$t('auth.user_adventures')}
	</h2>

	{#if adventures && adventures.length === 0}
		<p class="text-lg text-center text-base-content">
			{$t('auth.no_public_adventures')}
		</p>
	{:else}
		<div class="flex flex-wrap gap-4 mr-4 justify-center content-center">
			{#each adventures as adventure}
				<AdventureCard {adventure} user={null} />
			{/each}
		</div>
	{/if}

	<!-- Collections Section -->
	<div class="divider my-8"></div>

	<h2 class="text-2xl font-bold text-center mb-6 text-primary">
		{$t('auth.user_collections')}
	</h2>

	{#if collections && collections.length === 0}
		<p class="text-lg text-center text-base-content">
			{$t('auth.no_public_collections')}
		</p>
	{:else}
		<div class="flex flex-wrap gap-4 mr-4 justify-center content-center">
			{#each collections as collection}
				<CollectionCard {collection} type={''} />
			{/each}
		</div>
	{/if}
</section>

<svelte:head>
	<title>{user.first_name || user.username}'s Profile | AdventureLog</title>
	<meta name="description" content="User Profile" />
</svelte:head>
