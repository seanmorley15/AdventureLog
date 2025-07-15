<script lang="ts">
	export let data;
	import AdventureCard from '$lib/components/AdventureCard.svelte';
	import CollectionCard from '$lib/components/CollectionCard.svelte';
	import type { Adventure, Collection, User } from '$lib/types.js';
	import { t } from 'svelte-i18n';
	import { onMount } from 'svelte';
	import { gsap } from 'gsap';

	// Icons
	import Calendar from '~icons/mdi/calendar';
	import MapMarker from '~icons/mdi/map-marker';
	import Airplane from '~icons/mdi/airplane';
	import FlagCheckered from '~icons/mdi/flag-checkered-variant';
	import CityVariant from '~icons/mdi/city-variant-outline';
	import MapMarkerStar from '~icons/mdi/map-marker-star-outline';
	import CollectionIcon from '~icons/mdi/folder-multiple';
	import TrendingUp from '~icons/mdi/trending-up';
	import Share from '~icons/mdi/share-variant';
	import Award from '~icons/mdi/award';

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

	// Calculate achievements
	$: worldExplorationPercentage = stats
		? Math.round((stats.visited_country_count / stats.total_countries) * 100)
		: 0;
	$: regionExplorationPercentage = stats
		? Math.round((stats.visited_region_count / stats.total_regions) * 100)
		: 0;
	$: cityExplorationPercentage = stats
		? Math.round((stats.visited_city_count / stats.total_cities) * 100)
		: 0;

	// Achievement levels
	$: achievementLevel =
		(stats?.adventure_count ?? 0) >= 100
			? 'Legendary Explorer'
			: (stats?.adventure_count ?? 0) >= 75
				? 'World Wanderer'
				: (stats?.adventure_count ?? 0) >= 50
					? 'Explorer Master'
					: (stats?.adventure_count ?? 0) >= 35
						? 'Globetrotter'
						: (stats?.adventure_count ?? 0) >= 25
							? 'Seasoned Traveler'
							: (stats?.adventure_count ?? 0) >= 15
								? 'Adventure Seeker'
								: (stats?.adventure_count ?? 0) >= 10
									? 'Trailblazer'
									: (stats?.adventure_count ?? 0) >= 5
										? 'Journey Starter'
										: (stats?.adventure_count ?? 0) >= 1
											? 'Travel Enthusiast'
											: 'New Explorer';

	$: achievementColor =
		(stats?.adventure_count ?? 0) >= 50
			? 'text-warning'
			: (stats?.adventure_count ?? 0) >= 25
				? 'text-success'
				: (stats?.adventure_count ?? 0) >= 10
					? 'text-info'
					: (stats?.adventure_count ?? 0) >= 5
						? 'text-secondary'
						: 'text-primary';
</script>

<svelte:head>
	<title>{user.first_name || user.username}'s Profile | AdventureLog</title>
	<meta name="description" content="User Profile" />
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-base-200 via-base-100 to-base-200">
	<!-- Hero Profile Section -->
	<div class="relative overflow-hidden">
		<!-- Background Pattern -->
		<div class="absolute inset-0 bg-gradient-to-r from-primary/5 via-secondary/5 to-accent/5"></div>

		<div class="container mx-auto px-6 py-16 relative">
			<div class="profile-header flex flex-col items-center text-center">
				<!-- Profile Picture with Enhanced Styling -->
				<div class="relative mb-6">
					{#if user.profile_pic}
						<div class="avatar">
							<div
								class="w-32 h-32 rounded-full ring-4 ring-primary ring-offset-4 ring-offset-base-100 shadow-2xl"
							>
								<img src={user.profile_pic} alt="Profile" />
							</div>
						</div>
					{:else}
						<div class="avatar">
							<div
								class="w-32 h-32 rounded-full ring-4 ring-primary ring-offset-4 ring-offset-base-100 shadow-2xl bg-gradient-to-br from-primary to-secondary"
							>
								{#if user.first_name && user.last_name}
									<img
										src={`https://eu.ui-avatars.com/api/?name=${user.first_name}+${user.last_name}&size=250&background=random`}
										alt="Profile"
									/>
								{:else}
									<img
										src={`https://eu.ui-avatars.com/api/?name=${user.username}&size=250&background=random`}
										alt="Profile"
									/>
								{/if}
							</div>
						</div>
					{/if}
				</div>

				<!-- User Info -->
				<div class="space-y-4">
					{#if user && user.first_name && user.last_name}
						<h1
							class="text-5xl font-bold bg-gradient-to-r from-primary via-secondary to-accent bg-clip-text text-transparent"
						>
							{user.first_name}
							{user.last_name}
						</h1>
					{:else}
						<h1
							class="text-5xl font-bold bg-gradient-to-r from-primary via-secondary to-accent bg-clip-text text-transparent"
						>
							{user.username}
						</h1>
					{/if}

					<p class="text-xl text-base-content/70">@{user.username}</p>

					<!-- Member Since -->
					{#if user && user.date_joined}
						<div class="flex items-center justify-center gap-2 text-base-content/60">
							<Calendar class="w-5 h-5" />
							<span class="text-lg">
								{$t('profile.member_since')}
								{new Date(user.date_joined).toLocaleDateString(undefined, {
									timeZone: 'UTC',
									year: 'numeric',
									month: 'long'
								})}
							</span>
						</div>
					{/if}

					<!-- User rank achievement -->
					{#if stats && stats.adventure_count > 0}
						<div class="flex items-center justify-center gap-2 text-base-content/70">
							<Award class="w-5 h-5" />
							<span class={`text-lg ${achievementColor}`}>{achievementLevel}</span>
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>

	<div class="container mx-auto px-6 py-8">
		<!-- Enhanced Stats Section -->
		{#if stats}
			<div class="content-section mb-16">
				<div class="text-center mb-8">
					<h2 class="text-3xl font-bold mb-2">{$t('profile.travel_statistics')}</h2>
					<p class="text-base-content/60">{$t('profile.your_journey_at_a_glance')}</p>
				</div>

				<!-- Primary Stats Grid -->
				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
					<!-- Adventures -->
					<div
						class="stat-card card bg-gradient-to-br from-primary/10 to-primary/5 border border-primary/20 hover:shadow-2xl transition-all duration-300"
					>
						<div class="card-body p-6">
							<div class="flex items-center justify-between">
								<div>
									<div class="text-primary/70 font-medium text-sm uppercase tracking-wide">
										{$t('navbar.adventures')}
									</div>
									<div class="text-4xl font-bold text-primary">{stats.adventure_count}</div>
									<div class="text-primary/60 mt-2 flex items-center gap-1">
										<TrendingUp class="w-4 h-4" />
										{achievementLevel}
									</div>
								</div>
								<div class="p-4 bg-primary/20 rounded-2xl">
									<Airplane class="w-8 h-8 text-primary" />
								</div>
							</div>
						</div>
					</div>

					<!-- Collections -->
					<div
						class="stat-card card bg-gradient-to-br from-secondary/10 to-secondary/5 shadow-xl border border-secondary/20 hover:shadow-2xl transition-all duration-300"
					>
						<div class="card-body p-6">
							<div class="flex items-center justify-between">
								<div>
									<div class="text-secondary/70 font-medium text-sm uppercase tracking-wide">
										{$t('navbar.collections')}
									</div>
									<div class="text-4xl font-bold text-secondary">{stats.trips_count}</div>
									<div class="text-secondary/60 mt-2">{$t('profile.planned_trips')}</div>
								</div>
								<div class="p-4 bg-secondary/20 rounded-2xl">
									<CollectionIcon class="w-8 h-8 text-secondary" />
								</div>
							</div>
						</div>
					</div>

					<!-- Countries -->
					<div
						class="stat-card card bg-gradient-to-br from-success/10 to-success/5 border border-success/20 hover:shadow-2xl transition-all duration-300"
					>
						<div class="card-body p-6">
							<div class="flex items-center justify-between">
								<div class="flex-1">
									<div class="text-success/70 font-medium text-sm uppercase tracking-wide">
										{$t('profile.visited_countries')}
									</div>
									<div class="text-4xl font-bold text-success">{stats.visited_country_count}</div>
									<div class="text-success/60 mt-2">
										<div class="flex items-center justify-between mb-1">
											<span>{worldExplorationPercentage}% {$t('home.of_world')}</span>
											<span class="text-xs"
												>{stats.visited_country_count}/{stats.total_countries}</span
											>
										</div>
										<progress
											class="progress progress-success w-full h-2"
											value={stats.visited_country_count}
											max={stats.total_countries}
										></progress>
									</div>
								</div>
								<div class="p-4 bg-success/20 rounded-2xl">
									<FlagCheckered class="w-8 h-8 text-success" />
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- Secondary Stats -->
				<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
					<!-- Regions -->
					<div
						class="stat-card card bg-gradient-to-br from-info/10 to-info/5 border border-info/20 hover:shadow-2xl transition-all duration-300"
					>
						<div class="card-body p-6">
							<div class="flex items-center justify-between">
								<div class="flex-1">
									<div class="text-info/70 font-medium text-sm uppercase tracking-wide">
										{$t('profile.visited_regions')}
									</div>
									<div class="text-3xl font-bold text-info">{stats.visited_region_count}</div>
									<div class="text-info/60 mt-2">
										<div class="flex items-center justify-between mb-1">
											<span>{regionExplorationPercentage}% {$t('profile.explored')}</span>
											<span class="text-xs">{stats.visited_region_count}/{stats.total_regions}</span
											>
										</div>
										<progress
											class="progress progress-info w-full h-2"
											value={stats.visited_region_count}
											max={stats.total_regions}
										></progress>
									</div>
								</div>
								<div class="p-4 bg-info/20 rounded-2xl">
									<MapMarkerStar class="w-8 h-8 text-info" />
								</div>
							</div>
						</div>
					</div>

					<!-- Cities -->
					<div
						class="stat-card card bg-gradient-to-br from-warning/10 to-warning/5 shadow-xl border border-warning/20 hover:shadow-2xl transition-all duration-300"
					>
						<div class="card-body p-6">
							<div class="flex items-center justify-between">
								<div class="flex-1">
									<div class="text-warning/70 font-medium text-sm uppercase tracking-wide">
										{$t('profile.visited_cities')}
									</div>
									<div class="text-3xl font-bold text-warning">{stats.visited_city_count}</div>
									<div class="text-warning/60 mt-2">
										<div class="flex items-center justify-between mb-1">
											<span>{cityExplorationPercentage}% {$t('profile.discovered')}</span>
											<span class="text-xs">{stats.visited_city_count}/{stats.total_cities}</span>
										</div>
										<progress
											class="progress progress-warning w-full h-2"
											value={stats.visited_city_count}
											max={stats.total_cities}
										></progress>
									</div>
								</div>
								<div class="p-4 bg-warning/20 rounded-2xl">
									<CityVariant class="w-8 h-8 text-warning" />
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		{/if}

		<!-- Adventures Section -->
		<div class="content-section mb-16">
			<div class="flex items-center justify-between mb-8">
				<div class="flex items-center gap-3">
					<div class="p-2 bg-primary/10 rounded-xl">
						<Airplane class="w-6 h-6 text-primary" />
					</div>
					<div>
						<h2 class="text-3xl font-bold">{$t('auth.user_adventures')}</h2>
						<p class="text-base-content/60">{$t('profile.public_adventure_experiences')}</p>
					</div>
				</div>
				{#if adventures && adventures.length > 0}
					<div class="badge badge-primary badge-lg">
						{adventures.length}
						{adventures.length === 1 ? $t('adventures.adventure') : $t('navbar.adventures')}
					</div>
				{/if}
			</div>

			{#if adventures && adventures.length === 0}
				<div class="card bg-base-100">
					<div class="card-body text-center py-16">
						<div class="p-6 bg-base-200/50 rounded-2xl w-fit mx-auto mb-6">
							<Airplane class="w-16 h-16 text-base-content/30" />
						</div>
						<h3 class="text-xl font-bold text-base-content/70 mb-2">
							{$t('auth.no_public_adventures')}
						</h3>
						<p class="text-base-content/50">{$t('profile.no_shared_adventures')}</p>
					</div>
				</div>
			{:else}
				<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
					{#each adventures as adventure}
						<div class="adventure-card">
							<AdventureCard {adventure} user={null} />
						</div>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Collections Section -->
		<div class="content-section">
			<div class="flex items-center justify-between mb-8">
				<div class="flex items-center gap-3">
					<div class="p-2 bg-secondary/10 rounded-xl">
						<CollectionIcon class="w-6 h-6 text-secondary" />
					</div>
					<div>
						<h2 class="text-3xl font-bold">{$t('auth.user_collections')}</h2>
						<p class="text-base-content/60">{$t('profile.planned_trips')}</p>
					</div>
				</div>
				{#if collections && collections.length > 0}
					<div class="badge badge-secondary badge-lg">
						{collections.length}
						{collections.length === 1 ? $t('adventures.collection') : $t('navbar.collections')}
					</div>
				{/if}
			</div>

			{#if collections && collections.length === 0}
				<div class="card bg-base-100">
					<div class="card-body text-center py-16">
						<div class="p-6 bg-base-200/50 rounded-2xl w-fit mx-auto mb-6">
							<CollectionIcon class="w-16 h-16 text-base-content/30" />
						</div>
						<h3 class="text-xl font-bold text-base-content/70 mb-2">
							{$t('auth.no_public_collections')}
						</h3>
						<p class="text-base-content/50">{$t('profile.no_shared_collections')}</p>
					</div>
				</div>
			{:else}
				<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
					{#each collections as collection}
						<div class="collection-card">
							<CollectionCard {collection} type={''} user={null} />
						</div>
					{/each}
				</div>
			{/if}
		</div>
	</div>
</div>
