<script lang="ts">
	import AdventureCard from '$lib/components/AdventureCard.svelte';
	import type { PageData } from './$types';
	import { t } from 'svelte-i18n';
	import { onMount } from 'svelte';
	import { gsap } from 'gsap';

	// Icons
	import FlagCheckeredVariantIcon from '~icons/mdi/flag-checkered-variant';
	import Airplane from '~icons/mdi/airplane';
	import CityVariantOutline from '~icons/mdi/city-variant-outline';
	import MapMarkerStarOutline from '~icons/mdi/map-marker-star-outline';
	import TrendingUp from '~icons/mdi/trending-up';
	import CalendarClock from '~icons/mdi/calendar-clock';
	import Plus from '~icons/mdi/plus';

	export let data: PageData;

	const user = data.user;
	const recentAdventures = data.props.adventures;
	const stats = data.props.stats;

	// Calculate completion percentage
	$: completionPercentage =
		stats.visited_country_count > 0 ? Math.round((stats.visited_country_count / 195) * 100) : 0; // Assuming ~195 countries worldwide
</script>

<svelte:head>
	<title>Dashboard | AdventureLog</title>
	<meta name="description" content="Home dashboard for AdventureLog." />
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-base-200 via-base-100 to-base-200">
	<div class="container mx-auto px-6 py-8">
		<!-- Welcome Section -->
		<div class="welcome-section mb-12">
			<div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
				<div>
					<div class="flex items-center gap-4 mb-4">
						<!-- <div class="avatar placeholder">
							<div class="bg-primary text-primary-content rounded-full w-16 h-16">
								<span class="text-xl font-bold">
									{user?.first_name?.charAt(0) || user?.username?.charAt(0) || 'A'}
								</span>
							</div>
						</div> -->
						<div>
							<h1 class="text-4xl lg:text-5xl font-bold bg-clip-text text-black">
								{$t('dashboard.welcome_back')}, {user?.first_name
									? `${user.first_name}`
									: user?.username}!
							</h1>
							<p class="text-lg text-base-content/60 mt-2">
								{#if stats.adventure_count > 0}
									{$t('dashboard.welcome_text_1')}
									<span class="font-semibold text-primary">{stats.adventure_count}</span>
									{$t('dashboard.welcome_text_2')}
								{:else}
									{$t('dashboard.welcome_text_3')}
								{/if}
							</p>
						</div>
					</div>
				</div>

				<!-- Quick Action -->
				<div class="flex flex-col sm:flex-row gap-3">
					<a
						href="/adventures"
						class="btn btn-primary btn-lg gap-2 shadow-lg hover:shadow-xl transition-all duration-300 rounded-full"
					>
						<Plus class="w-5 h-5" />
						{$t('map.add_adventure')}
					</a>
					<a href="/worldtravel" class="btn btn-outline btn-lg gap-2 rounded-full">
						<FlagCheckeredVariantIcon class="w-5 h-5" />
						{$t('home.explore_world')}
					</a>
				</div>
			</div>
		</div>

		<!-- Stats Grid -->
		<div
			class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3 gap-8 mb-12"
		>
			<!-- Countries Visited -->
			<div
				class="stat-card card bg-gradient-to-br from-primary/10 to-primary/5 border border-primary/20 hover:shadow-2xl transition-all duration-300"
			>
				<div class="card-body p-6">
					<div class="flex items-center justify-between">
						<div class="flex-1">
							<div class="stat-title text-primary/70 font-medium">
								{$t('dashboard.countries_visited')}
							</div>
							<div class="stat-value text-3xl font-bold text-primary">
								{stats.visited_country_count}
							</div>
							<div class="stat-desc text-primary/60 mt-2">
								<div class="flex items-center justify-between">
									<span class="font-medium">{completionPercentage}% {$t('home.of_world')}</span>
								</div>
								<progress
									class="progress progress-primary w-full mt-1"
									value={stats.visited_country_count}
									max="195"
								></progress>
							</div>
						</div>
						<div class="p-4 bg-primary/20 rounded-2xl">
							<FlagCheckeredVariantIcon class="w-8 h-8 text-primary" />
						</div>
					</div>
				</div>
			</div>

			<!-- Regions Visited -->
			<div
				class="stat-card card bg-gradient-to-br from-success/10 to-success/5 border border-success/20 hover:shadow-2xl transition-all duration-300"
			>
				<div class="card-body p-6">
					<div class="flex items-center justify-between">
						<div>
							<div class="stat-title text-success/70 font-medium">
								{$t('dashboard.total_visited_regions')}
							</div>
							<div class="stat-value text-3xl font-bold text-success">
								{stats.visited_region_count}
							</div>
						</div>
						<div class="p-4 bg-success/20 rounded-2xl">
							<MapMarkerStarOutline class="w-8 h-8 text-success" />
						</div>
					</div>
				</div>
			</div>

			<!-- Cities Visited -->
			<div
				class="stat-card card bg-gradient-to-br from-info/10 to-info/5 border border-info/20 hover:shadow-2xl transition-all duration-300"
			>
				<div class="card-body p-6">
					<div class="flex items-center justify-between">
						<div>
							<div class="stat-title text-info/70 font-medium">
								{$t('dashboard.total_visited_cities')}
							</div>
							<div class="stat-value text-3xl font-bold text-info">{stats.visited_city_count}</div>
						</div>
						<div class="p-4 bg-info/20 rounded-2xl">
							<CityVariantOutline class="w-8 h-8 text-info" />
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Recent Adventures Section -->
		{#if recentAdventures.length > 0}
			<div class="mb-8">
				<div class="flex items-center justify-between mb-6">
					<div class="flex items-center gap-3">
						<div class="p-2 bg-primary/10 rounded-xl">
							<CalendarClock class="w-6 h-6 text-primary" />
						</div>
						<div>
							<h2 class="text-3xl font-bold">{$t('dashboard.recent_adventures')}</h2>
							<p class="text-base-content/60">{$t('home.latest_travel_experiences')}</p>
						</div>
					</div>
					<a href="/adventures" class="btn btn-ghost gap-2">
						{$t('dashboard.view_all')}
						<span class="badge badge-primary">{stats.adventure_count}</span>
					</a>
				</div>

				<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
					{#each recentAdventures as adventure}
						<div class="adventure-card">
							<AdventureCard {adventure} user={data.user} readOnly />
						</div>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Empty State / Inspiration -->
		{#if recentAdventures.length === 0}
			<div
				class="empty-state card bg-gradient-to-br from-base-100 to-base-200 border border-base-300"
			>
				<div class="card-body p-12 text-center">
					<div class="flex justify-center mb-6">
						<div class="p-6 bg-primary/10 rounded-3xl">
							<Airplane class="w-16 h-16 text-primary" />
						</div>
					</div>

					<h2
						class="text-3xl font-bold mb-4 bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent"
					>
						{$t('dashboard.no_recent_adventures')}
					</h2>
					<p class="text-lg text-base-content/60 mb-8 max-w-md mx-auto leading-relaxed">
						{$t('dashboard.document_some_adventures')}
					</p>

					<div class="flex flex-col sm:flex-row gap-4 justify-center">
						<a
							href="/adventures"
							class="btn btn-primary btn-lg gap-2 shadow-lg hover:shadow-xl transition-all duration-300 rounded-full font-normal"
						>
							<Plus class="w-5 h-5" />
							{$t('map.add_adventure')}
						</a>
						<a href="/worldtravel" class="btn btn-outline btn-lg gap-2 rounded-full font-normal">
							<FlagCheckeredVariantIcon class="w-5 h-5" />
							{$t('home.explore_world')}
						</a>
					</div>
				</div>
			</div>
		{/if}
	</div>
</div>
