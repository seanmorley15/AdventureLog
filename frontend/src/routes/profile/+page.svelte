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

	if (data.stats) {
		stats = data.stats;
	} else {
		stats = null;
	}
	console.log(stats);
</script>

{#if data.user.profile_pic}
	<div class="avatar flex items-center justify-center">
		<div class="w-24 rounded">
			<!-- svelte-ignore a11y-missing-attribute -->
			<img src={data.user.profile_pic} class="w-24 rounded-full" />
		</div>
	</div>
{/if}

{#if data.user && data.user.first_name && data.user.last_name}
	<h1 class="text-center text-4xl font-bold">
		{data.user.first_name}
		{data.user.last_name}
	</h1>
{/if}
<p class="text-center text-lg mt-2">{data.user.username}</p>

{#if data.user && data.user.date_joined}
	<p class="ml-1 text-lg text-center mt-4">{$t('profile.member_since')}</p>
	<div class="flex items-center justify-center text-center">
		<iconify-icon icon="mdi:calendar" class="text-2xl"></iconify-icon>
		<p class="ml-1 text-xl">
			{new Date(data.user.date_joined).toLocaleDateString(undefined, { timeZone: 'UTC' })}
		</p>
	</div>
{/if}

{#if stats}
	<!-- divider -->
	<div class="divider pr-8 pl-8"></div>

	<h1 class="text-center text-2xl font-bold mt-8 mb-2">{$t('profile.user_stats')}</h1>

	<div class="flex justify-center items-center">
		<div class="stats stats-vertical lg:stats-horizontal shadow bg-base-200">
			<div class="stat">
				<div class="stat-title">{$t('navbar.adventures')}</div>
				<div class="stat-value text-center">{stats.adventure_count}</div>
				<!-- <div class="stat-desc">Jan 1st - Feb 1st</div> -->
			</div>
			<div class="stat">
				<div class="stat-title">{$t('navbar.collections')}</div>
				<div class="stat-value text-center">{stats.trips_count}</div>
				<!-- <div class="stat-desc">↘︎ 90 (14%)</div> -->
			</div>

			<div class="stat">
				<div class="stat-title">{$t('profile.visited_countries')}</div>
				<div class="stat-value text-center">
					{Math.round((stats.country_count / stats.total_countries) * 100)}%
				</div>
				<div class="stat-desc">
					{stats.country_count}/{stats.total_countries}
				</div>
			</div>

			<div class="stat">
				<div class="stat-title">{$t('profile.visited_regions')}</div>
				<div class="stat-value text-center">
					{Math.round((stats.visited_region_count / stats.total_regions) * 100)}%
				</div>
				<div class="stat-desc">
					{stats.visited_region_count}/{stats.total_regions}
				</div>
			</div>
		</div>
	</div>
{/if}

<svelte:head>
	<title>Profile | AdventureLog</title>
	<meta name="description" content="{data.user.first_name}'s profile on AdventureLog." />
</svelte:head>
