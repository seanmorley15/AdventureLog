<script lang="ts">
	export let data;
	import LocationCard from '$lib/components/LocationCard.svelte';
	import CollectionCard from '$lib/components/CollectionCard.svelte';
	import type { Location, Collection, User } from '$lib/types.js';
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
	import Run from '~icons/mdi/run';
	import Timer from '~icons/mdi/timer-outline';
	import TrendingUpOutline from '~icons/mdi/trending-up';
	import Mountain from '~icons/mdi/mountain';
	import Walk from '~icons/mdi/walk';
	import Bike from '~icons/mdi/bike';
	import Snowflake from '~icons/mdi/snowflake';
	import WaterOutline from '~icons/mdi/water-outline';
	import Dumbbell from '~icons/mdi/dumbbell';
	import TennisOutline from '~icons/mdi/tennis';
	import RockClimbing from '~icons/mdi/image-filter-hdr';
	import Soccer from '~icons/mdi/soccer';
	import DotsHorizontal from '~icons/mdi/dots-horizontal';
	import Fire from '~icons/mdi/fire';
	import ChevronDown from '~icons/mdi/chevron-down';
	import ChevronUp from '~icons/mdi/chevron-up';

	let measurementSystem = data.user?.measurement_system || 'metric';
	let expandedCategories = new Set();

	let stats: {
		visited_country_count: number;
		total_regions: number;
		trips_count: number;
		location_count: number;
		visited_region_count: number;
		total_countries: number;
		visited_city_count: number;
		total_cities: number;
		activities_overall: {
			total_count: number;
			total_distance: number;
			total_moving_time: number;
			total_elevation_gain: number;
			total_elevation_loss: number;
			total_calories: number;
		};
		activities_by_category: Record<
			string,
			{
				count: number;
				total_distance: number;
				total_moving_time: number;
				total_elevation_gain: number;
				total_elevation_loss: number;
				avg_distance: number;
				max_distance: number;
				avg_elevation_gain: number;
				max_elevation_gain: number;
				avg_speed: number;
				max_speed: number;
				total_calories: number;
				sports: Record<
					string,
					{
						count: number;
						total_distance: number;
						total_elevation_gain: number;
					}
				>;
			}
		>;
		// Legacy fields
		activity_count: number;
		activity_distance: number;
		activity_moving_time: number;
		activity_elevation: number;
	} | null;

	const user: User = data.user;
	const adventures: Location[] = data.adventures;
	const collections: Collection[] = data.collections;
	stats = data.stats || null;

	// Activity category configurations
	const categoryConfig: Record<
		string,
		{
			name: string;
			icon: any;
			color: string;
			bgGradient: string;
			borderColor: string;
		}
	> = {
		running: {
			name: 'Running',
			icon: Run,
			color: 'error',
			bgGradient: 'from-error/10 to-error/5',
			borderColor: 'border-error/20'
		},
		walking_hiking: {
			name: 'Walking & Hiking',
			icon: Walk,
			color: 'success',
			bgGradient: 'from-success/10 to-success/5',
			borderColor: 'border-success/20'
		},
		cycling: {
			name: 'Cycling',
			icon: Bike,
			color: 'info',
			bgGradient: 'from-info/10 to-info/5',
			borderColor: 'border-info/20'
		},
		winter_sports: {
			name: 'Winter Sports',
			icon: Snowflake,
			color: 'primary',
			bgGradient: 'from-primary/10 to-primary/5',
			borderColor: 'border-primary/20'
		},
		water_sports: {
			name: 'Water Sports',
			icon: WaterOutline,
			color: 'accent',
			bgGradient: 'from-accent/10 to-accent/5',
			borderColor: 'border-accent/20'
		},
		fitness_gym: {
			name: 'Fitness & Gym',
			icon: Dumbbell,
			color: 'warning',
			bgGradient: 'from-warning/10 to-warning/5',
			borderColor: 'border-warning/20'
		},
		racket_sports: {
			name: 'Racket Sports',
			icon: TennisOutline,
			color: 'secondary',
			bgGradient: 'from-secondary/10 to-secondary/5',
			borderColor: 'border-secondary/20'
		},
		climbing_adventure: {
			name: 'Climbing & Adventure',
			icon: RockClimbing,
			color: 'orange-500',
			bgGradient: 'from-orange-500/10 to-orange-500/5',
			borderColor: 'border-orange-500/20'
		},
		team_sports: {
			name: 'Team Sports',
			icon: Soccer,
			color: 'green-500',
			bgGradient: 'from-green-500/10 to-green-500/5',
			borderColor: 'border-green-500/20'
		},
		other_sports: {
			name: 'Other Sports',
			icon: DotsHorizontal,
			color: 'purple-500',
			bgGradient: 'from-purple-500/10 to-purple-500/5',
			borderColor: 'border-purple-500/20'
		}
	};

	function toggleCategory(category: string) {
		if (expandedCategories.has(category)) {
			expandedCategories.delete(category);
		} else {
			expandedCategories.add(category);
		}
		expandedCategories = expandedCategories; // Trigger reactivity
	}

	// function to take in meters for distance and return it in either kilometers or miles
	function getDistance(meters: number): string {
		return measurementSystem === 'imperial'
			? `${(meters * 0.000621371).toFixed(2)} mi`
			: `${(meters / 1000).toFixed(2)} km`;
	}

	function getElevation(meters: number): string {
		return measurementSystem === 'imperial'
			? `${(meters * 3.28084).toFixed(1)} ft`
			: `${meters.toFixed(1)} m`;
	}

	// Function to format time from seconds to readable format
	function formatTime(seconds: number): string {
		const hours = Math.floor(seconds / 3600);
		const minutes = Math.floor((seconds % 3600) / 60);

		if (hours > 0) {
			return `${hours}h ${minutes}m`;
		}
		return `${minutes}m`;
	}

	function getSpeed(ms: number): string {
		if (measurementSystem === 'imperial') {
			const mph = ms * 2.237;
			return `${mph.toFixed(1)} mph`;
		} else {
			const kmh = ms * 3.6;
			return `${kmh.toFixed(1)} km/h`;
		}
	}

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
		(stats?.location_count ?? 0) >= 100
			? 'Legendary Explorer'
			: (stats?.location_count ?? 0) >= 75
				? 'World Wanderer'
				: (stats?.location_count ?? 0) >= 50
					? 'Explorer Master'
					: (stats?.location_count ?? 0) >= 35
						? 'Globetrotter'
						: (stats?.location_count ?? 0) >= 25
							? 'Seasoned Traveler'
							: (stats?.location_count ?? 0) >= 15
								? 'Adventure Seeker'
								: (stats?.location_count ?? 0) >= 10
									? 'Trailblazer'
									: (stats?.location_count ?? 0) >= 5
										? 'Journey Starter'
										: (stats?.location_count ?? 0) >= 1
											? 'Travel Enthusiast'
											: 'New Explorer';

	$: achievementColor =
		(stats?.location_count ?? 0) >= 50
			? 'text-warning'
			: (stats?.location_count ?? 0) >= 25
				? 'text-success'
				: (stats?.location_count ?? 0) >= 10
					? 'text-info'
					: (stats?.location_count ?? 0) >= 5
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
					{#if stats && stats.location_count > 0}
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
						class="stat-card card bg-gradient-to-br from-primary/10 to-primary/5 shadow-xl border border-primary/20 hover:shadow-2xl transition-all duration-300"
					>
						<div class="card-body p-6">
							<div class="flex items-center justify-between">
								<div>
									<div class="text-primary/70 font-medium text-sm uppercase tracking-wide">
										{$t('locations.locations')}
									</div>
									<div class="text-4xl font-bold text-primary">{stats.location_count}</div>
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
						class="stat-card card bg-gradient-to-br from-success/10 to-success/5 shadow-xl border border-success/20 hover:shadow-2xl transition-all duration-300"
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
				<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
					<!-- Regions -->
					<div
						class="stat-card card bg-gradient-to-br from-info/10 to-info/5 shadow-xl border border-info/20 hover:shadow-2xl transition-all duration-300"
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

				<!-- Enhanced Activity Stats Section -->
				{#if stats.activities_overall && stats.activities_overall.total_count > 0}
					<div class="mb-8">
						<div class="text-center mb-6">
							<h3 class="text-2xl font-bold mb-2">{$t('adventures.activity_statistics')}</h3>
							<p class="text-base-content/60">{$t('adventures.activity_statistics_description')}</p>
						</div>

						<!-- Overall Activity Summary -->
						<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
							<!-- Total Activities -->
							<div
								class="stat-card card bg-gradient-to-br from-accent/10 to-accent/5 shadow-xl border border-accent/20 hover:shadow-2xl transition-all duration-300"
							>
								<div class="card-body p-6">
									<div class="flex items-center justify-between">
										<div>
											<div class="text-accent/70 font-medium text-sm uppercase tracking-wide">
												{$t('adventures.total_activities')}
											</div>
											<div class="text-3xl font-bold text-accent">
												{stats.activities_overall.total_count}
											</div>
											<div class="text-accent/60 mt-2">{$t('adventures.recorded_sessions')}</div>
										</div>
										<div class="p-3 bg-accent/20 rounded-2xl">
											<Run class="w-6 h-6 text-accent" />
										</div>
									</div>
								</div>
							</div>

							<!-- Total Distance -->
							<div
								class="stat-card card bg-gradient-to-br from-error/10 to-error/5 shadow-xl border border-error/20 hover:shadow-2xl transition-all duration-300"
							>
								<div class="card-body p-6">
									<div class="flex items-center justify-between">
										<div>
											<div class="text-error/70 font-medium text-sm uppercase tracking-wide">
												{$t('adventures.total_distance')}
											</div>
											<div class="text-3xl font-bold text-error">
												{getDistance(stats.activities_overall.total_distance)}
											</div>
											<div class="text-error/60 mt-2">{$t('adventures.distance_covered')}</div>
										</div>
										<div class="p-3 bg-error/20 rounded-2xl">
											<TrendingUpOutline class="w-6 h-6 text-error" />
										</div>
									</div>
								</div>
							</div>

							<!-- Moving Time -->
							<div
								class="stat-card card bg-gradient-to-br from-purple-500/10 to-purple-500/5 shadow-xl border border-purple-500/20 hover:shadow-2xl transition-all duration-300"
							>
								<div class="card-body p-6">
									<div class="flex items-center justify-between">
										<div>
											<div class="text-purple-500/70 font-medium text-sm uppercase tracking-wide">
												{$t('adventures.moving_time')}
											</div>
											<div class="text-3xl font-bold text-purple-500">
												{formatTime(stats.activities_overall.total_moving_time)}
											</div>
											<div class="text-purple-500/60 mt-2">{$t('adventures.active_duration')}</div>
										</div>
										<div class="p-3 bg-purple-500/20 rounded-2xl">
											<Timer class="w-6 h-6 text-purple-500" />
										</div>
									</div>
								</div>
							</div>

							<!-- Elevation Gain -->
							<div
								class="stat-card card bg-gradient-to-br from-orange-500/10 to-orange-500/5 shadow-xl border border-orange-500/20 hover:shadow-2xl transition-all duration-300"
							>
								<div class="card-body p-6">
									<div class="flex items-center justify-between">
										<div>
											<div class="text-orange-500/70 font-medium text-sm uppercase tracking-wide">
												{$t('adventures.elevation_gain')}
											</div>
											<div class="text-3xl font-bold text-orange-500">
												{getElevation(stats.activities_overall.total_elevation_gain)}
											</div>
											<div class="text-orange-500/60 mt-2">{$t('adventures.total_climbed')}</div>
										</div>
										<div class="p-3 bg-orange-500/20 rounded-2xl">
											<Mountain class="w-6 h-6 text-orange-500" />
										</div>
									</div>
								</div>
							</div>
						</div>

						<!-- Activity Categories -->
						<div class="space-y-4">
							<h4 class="text-xl font-bold text-center mb-6">
								{$t('adventures.activity_breakdown_by_category')}
							</h4>

							{#each Object.entries(stats.activities_by_category) as [categoryKey, categoryData]}
								{@const config = categoryConfig[categoryKey]}
								{@const isExpanded = expandedCategories.has(categoryKey)}

								<div
									class="card bg-gradient-to-br {config.bgGradient} shadow-xl border {config.borderColor} hover:shadow-2xl transition-all duration-300"
								>
									<div class="card-body p-6">
										<!-- Category Header -->
										<div
											class="flex items-center justify-between cursor-pointer"
											role="button"
											tabindex="0"
											on:click={() => toggleCategory(categoryKey)}
											on:keydown={(e) => {
												if (e.key === 'Enter' || e.key === ' ') {
													e.preventDefault();
													toggleCategory(categoryKey);
												}
											}}
										>
											<div class="flex items-center gap-4">
												<div class="p-3 bg-{config.color}/20 rounded-2xl">
													<svelte:component
														this={config.icon}
														class="w-6 h-6 text-{config.color}"
													/>
												</div>
												<div>
													<h5 class="text-xl font-bold text-{config.color}">{config.name}</h5>
													<p class="text-{config.color}/60">
														{categoryData.count}
														{$t('adventures.activities_text')}
													</p>
												</div>
											</div>
											<div class="flex items-center gap-4">
												<div class="text-right">
													<div class="text-2xl font-bold text-{config.color}">
														{getDistance(categoryData.total_distance)}
													</div>
													<div class="text-{config.color}/60 text-sm">
														{getElevation(categoryData.total_elevation_gain)}
														{$t('adventures.elevation')}
													</div>
												</div>
												<svelte:component
													this={isExpanded ? ChevronUp : ChevronDown}
													class="w-5 h-5 text-{config.color}/60"
												/>
											</div>
										</div>

										<!-- Expanded Details -->
										{#if isExpanded}
											<div class="mt-6 space-y-6">
												<!-- Quick Stats Grid -->
												<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
													<div
														class="bg-{config.color}/5 rounded-lg p-4 border {config.borderColor}"
													>
														<div class="text-{config.color}/70 text-xs uppercase font-medium">
															Time
														</div>
														<div class="text-lg font-bold text-{config.color}">
															{formatTime(categoryData.total_moving_time)}
														</div>
													</div>
													<div
														class="bg-{config.color}/5 rounded-lg p-4 border {config.borderColor}"
													>
														<div class="text-{config.color}/70 text-xs uppercase font-medium">
															Avg Speed
														</div>
														<div class="text-lg font-bold text-{config.color}">
															{getSpeed(categoryData.avg_speed)}
														</div>
													</div>
													<div
														class="bg-{config.color}/5 rounded-lg p-4 border {config.borderColor}"
													>
														<div class="text-{config.color}/70 text-xs uppercase font-medium">
															Max Distance
														</div>
														<div class="text-lg font-bold text-{config.color}">
															{getDistance(categoryData.max_distance)}
														</div>
													</div>
													{#if categoryData.total_calories > 0}
														<div
															class="bg-{config.color}/5 rounded-lg p-4 border {config.borderColor}"
														>
															<div class="text-{config.color}/70 text-xs uppercase font-medium">
																{$t('adventures.calories')}
															</div>
															<div
																class="text-lg font-bold text-{config.color} flex items-center gap-1"
															>
																<Fire class="w-4 h-4" />
																{Math.round(categoryData.total_calories)}
															</div>
														</div>
													{/if}
												</div>

												<!-- Individual Sports Breakdown -->
												{#if Object.keys(categoryData.sports).length > 1}
													<div>
														<h6 class="font-semibold text-{config.color} mb-3">Sport Types</h6>
														<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
															{#each Object.entries(categoryData.sports) as [sportType, sportData]}
																<div
																	class="bg-{config.color}/5 rounded-lg p-4 border {config.borderColor}"
																>
																	<div class="flex justify-between items-start">
																		<div>
																			<div class="font-medium text-{config.color}">{sportType}</div>
																			<div class="text-{config.color}/60 text-sm">
																				{sportData.count}
																				{$t('adventures.activities_text')}
																			</div>
																		</div>
																		<div class="text-right">
																			<div class="font-bold text-{config.color}">
																				{getDistance(sportData.total_distance)}
																			</div>
																			<div class="text-{config.color}/60 text-xs">
																				{getElevation(sportData.total_elevation_gain)} elev
																			</div>
																		</div>
																	</div>
																</div>
															{/each}
														</div>
													</div>
												{/if}
											</div>
										{/if}
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/if}
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
						<h2 class="text-3xl font-bold">{$t('auth.user_locations')}</h2>
						<p class="text-base-content/60">{$t('profile.public_location_experiences')}</p>
					</div>
				</div>
				{#if adventures && adventures.length > 0}
					<div class="badge badge-primary badge-lg">
						{adventures.length}
						{adventures.length === 1 ? $t('locations.location') : $t('locations.locations')}
					</div>
				{/if}
			</div>

			{#if adventures && adventures.length === 0}
				<div class="card bg-base-100 shadow-xl">
					<div class="card-body text-center py-16">
						<div class="p-6 bg-base-200/50 rounded-2xl w-fit mx-auto mb-6">
							<Airplane class="w-16 h-16 text-base-content/30" />
						</div>
						<h3 class="text-xl font-bold text-base-content/70 mb-2">
							{$t('auth.no_public_locations')}
						</h3>
						<p class="text-base-content/50">{$t('profile.no_shared_adventures')}</p>
					</div>
				</div>
			{:else}
				<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
					{#each adventures as adventure}
						<div class="adventure-card">
							<LocationCard {adventure} user={null} />
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
				<div class="card bg-base-100 shadow-xl">
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

<style>
	.stat-card:hover {
		transform: translateY(-2px);
	}

	.adventure-card:hover,
	.collection-card:hover {
		transform: translateY(-4px);
		transition: all 0.3s ease;
	}
</style>
