<script lang="ts">
	export let data;
	import { t } from 'svelte-i18n';

	let stats: {
		country_count: number;
		total_regions: number;
		trips_count: number;
		adventure_count: number;
		visited_region_count: number;
		total_countries: number;
	} | null;

	stats = data.stats || null;
</script>

<section class="min-h-screen bg-base-100 py-8 px-4">
	<div class="flex flex-col items-center">
		<!-- Profile Picture -->
		{#if data.user.profile_pic}
			<div class="avatar">
				<div
					class="w-24 rounded-full ring ring-primary ring-offset-base-100 ring-offset-2 shadow-md"
				>
					<img src={data.user.profile_pic} alt="Profile" />
				</div>
			</div>
		{/if}

		<!-- User Name -->
		{#if data.user && data.user.first_name && data.user.last_name}
			<h1 class="text-4xl font-bold text-primary mt-4">
				{data.user.first_name}
				{data.user.last_name}
			</h1>
		{/if}
		<p class="text-lg text-base-content mt-2">{data.user.username}</p>

		<!-- Member Since -->
		{#if data.user && data.user.date_joined}
			<div class="mt-4 flex items-center text-center text-base-content">
				<p class="text-lg font-medium">{$t('profile.member_since')}</p>
				<div class="flex items-center ml-2">
					<iconify-icon icon="mdi:calendar" class="text-2xl text-primary"></iconify-icon>
					<p class="ml-2 text-lg">
						{new Date(data.user.date_joined).toLocaleDateString(undefined, { timeZone: 'UTC' })}
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
						{Math.round((stats.country_count / stats.total_countries) * 100)}%
					</div>
					<div class="stat-desc text-center">
						{stats.country_count}/{stats.total_countries}
					</div>
				</div>

				<div class="stat">
					<div class="stat-title">{$t('profile.visited_regions')}</div>
					<div class="stat-value text-center">
						{Math.round((stats.visited_region_count / stats.total_regions) * 100)}%
					</div>
					<div class="stat-desc text-center">
						{stats.visited_region_count}/{stats.total_regions}
					</div>
				</div>
			</div>
		</div>
	{/if}
</section>

<svelte:head>
	<title>Profile | AdventureLog</title>
	<meta name="description" content="{data.user.first_name}'s profile on AdventureLog." />
</svelte:head>
