<script lang="ts">
	import type { AdditionalAdventure } from '$lib/types';
	import { onMount } from 'svelte';
	import type { PageData } from './$types';
	import { goto } from '$app/navigation';
	import Lost from '$lib/assets/undraw_lost.svg';
	import { DefaultMarker, MapLibre, Popup, GeoJSON, LineLayer } from 'svelte-maplibre';
	import { t } from 'svelte-i18n';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	// @ts-ignore
	import toGeoJSON from '@mapbox/togeojson';
	// @ts-ignore
	import { DateTime } from 'luxon';

	import LightbulbOn from '~icons/mdi/lightbulb-on';
	import WeatherSunset from '~icons/mdi/weather-sunset';
	import ClipboardList from '~icons/mdi/clipboard-list';
	import AdventureModal from '$lib/components/AdventureModal.svelte';
	import ImageDisplayModal from '$lib/components/ImageDisplayModal.svelte';
	import AttachmentCard from '$lib/components/AttachmentCard.svelte';
	import { getBasemapUrl, isAllDay } from '$lib';

	let geojson: any;

	const renderMarkdown = (markdown: string) => {
		return marked(markdown) as string;
	};

	async function getGpxFiles() {
		let gpxfiles: string[] = [];

		if (adventure.attachments && adventure.attachments.length > 0) {
			gpxfiles = adventure.attachments
				.filter((attachment) => attachment.extension === 'gpx')
				.map((attachment) => attachment.file);
		}

		geojson = {
			type: 'FeatureCollection',
			features: []
		};

		if (gpxfiles.length > 0) {
			const promises = gpxfiles.map(async (gpxfile) => {
				try {
					const gpxFileName = gpxfile.split('/').pop();
					const res = await fetch('/gpx/' + gpxFileName);

					if (!res.ok) {
						console.error(`Failed to fetch GPX file: ${gpxFileName}`);
						return [];
					}

					const gpxData = await res.text();
					const parser = new DOMParser();
					const gpx = parser.parseFromString(gpxData, 'text/xml');

					const convertedGeoJSON = toGeoJSON.gpx(gpx);
					return convertedGeoJSON.features || [];
				} catch (error) {
					console.error(`Error processing GPX file ${gpxfile}:`, error);
					return [];
				}
			});

			const results = await Promise.allSettled(promises);

			results.forEach((result) => {
				if (result.status === 'fulfilled' && result.value.length > 0) {
					geojson.features.push(...result.value);
				}
			});
		}
	}

	export let data: PageData;
	console.log(data);

	let adventure: AdditionalAdventure;
	let currentSlide = 0;

	function goToSlide(index: number) {
		currentSlide = index;
	}

	let notFound: boolean = false;
	let isEditModalOpen: boolean = false;
	let image_url: string | null = null;

	onMount(async () => {
		if (data.props.adventure) {
			adventure = data.props.adventure;
			adventure.images.sort((a, b) => {
				if (a.is_primary && !b.is_primary) {
					return -1;
				} else if (!a.is_primary && b.is_primary) {
					return 1;
				} else {
					return 0;
				}
			});
		} else {
			notFound = true;
		}
		await getGpxFiles();
	});

	async function saveEdit(event: CustomEvent<AdditionalAdventure>) {
		adventure = event.detail;
		isEditModalOpen = false;
		geojson = null;
		await getGpxFiles();
	}
</script>

{#if notFound}
	<div class="hero min-h-screen bg-gradient-to-br from-base-200 to-base-300 overflow-x-hidden">
		<div class="hero-content text-center">
			<div class="max-w-md">
				<img src={Lost} alt="Lost" class="w-64 mx-auto mb-8 opacity-80" />
				<h1 class="text-5xl font-bold text-primary mb-4">{$t('adventures.not_found')}</h1>
				<p class="text-lg opacity-70 mb-8">{$t('adventures.not_found_desc')}</p>
				<button class="btn btn-primary btn-lg" on:click={() => goto('/')}>
					{$t('adventures.homepage')}
				</button>
			</div>
		</div>
	</div>
{/if}

{#if isEditModalOpen}
	<AdventureModal
		adventureToEdit={adventure}
		on:close={() => (isEditModalOpen = false)}
		on:save={saveEdit}
	/>
{/if}

{#if image_url}
	<ImageDisplayModal image={image_url} on:close={() => (image_url = null)} {adventure} />
{/if}

{#if !adventure && !notFound}
	<div class="hero min-h-screen overflow-x-hidden">
		<div class="hero-content">
			<span class="loading loading-spinner w-24 h-24 text-primary"></span>
		</div>
	</div>
{/if}

{#if adventure}
	{#if data.user && data.user.uuid == adventure.user_id}
		<div class="fixed bottom-6 right-6 z-50">
			<button
				class="btn btn-primary btn-circle w-16 h hover:shadow-2xl transition-all duration-300 hover:scale-110"
				on:click={() => (isEditModalOpen = true)}
			>
				<ClipboardList class="w-8 h-8" />
			</button>
		</div>
	{/if}

	<!-- Hero Section -->
	<div class="relative">
		{#if adventure.images && adventure.images.length > 0}
			<div class="hero min-h-[60vh] relative overflow-hidden">
				<div class="hero-overlay bg-gradient-to-t from-black/70 via-black/20 to-transparent"></div>
				{#each adventure.images as image, i}
					<div
						class="absolute inset-0 transition-opacity duration-500"
						class:opacity-100={i === currentSlide}
						class:opacity-0={i !== currentSlide}
					>
						<button
							class="w-full h-full p-0 bg-transparent border-0"
							on:click={() => (image_url = image.image)}
							aria-label={`View full image of ${adventure.name}`}
						>
							<img src={image.image} class="w-full h-full object-cover" alt={adventure.name} />
						</button>
					</div>
				{/each}

				<div class="hero-content relative z-10 text-center text-white">
					<div class="max-w-4xl">
						<h1 class="text-6xl font-bold mb-4 drop-shadow-lg">{adventure.name}</h1>

						<!-- Rating -->
						{#if adventure.rating !== undefined && adventure.rating !== null}
							<div class="flex justify-center mb-6">
								<div class="rating rating-lg">
									{#each Array.from({ length: 5 }, (_, i) => i + 1) as star}
										<input
											type="radio"
											name="rating-hero"
											class="mask mask-star-2 bg-warning"
											checked={star <= adventure.rating}
											disabled
										/>
									{/each}
								</div>
							</div>
						{/if}

						<!-- Quick Info Cards -->
						<div class="flex flex-wrap justify-center gap-4 mb-6">
							<div class="badge badge-lg badge-primary font-semibold px-4 py-3">
								{adventure.category?.display_name}
								{adventure.category?.icon}
							</div>
							{#if adventure.location}
								<div class="badge badge-lg badge-secondary font-semibold px-4 py-3">
									📍 {adventure.location}
								</div>
							{/if}
							{#if adventure.visits.length > 0}
								<div class="badge badge-lg badge-accent font-semibold px-4 py-3">
									🎯 {adventure.visits.length}
									{adventure.visits.length === 1 ? $t('adventures.visit') : $t('adventures.visits')}
								</div>
							{/if}
						</div>

						<!-- Image Navigation -->
						{#if adventure.images.length > 1}
							<div class="w-full max-w-md mx-auto">
								<!-- Navigation arrows and current position indicator -->
								<div class="flex items-center justify-center gap-4 mb-3">
									<button
										on:click={() =>
											goToSlide(currentSlide > 0 ? currentSlide - 1 : adventure.images.length - 1)}
										class="btn btn-circle btn-sm btn-primary"
										aria-label="Previous image"
									>
										❮
									</button>

									<div class="text-sm font-medium bg-black/50 px-3 py-1 rounded-full">
										{currentSlide + 1} / {adventure.images.length}
									</div>

									<button
										on:click={() =>
											goToSlide(currentSlide < adventure.images.length - 1 ? currentSlide + 1 : 0)}
										class="btn btn-circle btn-sm btn-primary"
										aria-label="Next image"
									>
										❯
									</button>
								</div>

								<!-- Scrollable dot navigation for many images -->
								{#if adventure.images.length <= 12}
									<!-- Show all dots for 12 or fewer images -->
									<div class="flex justify-center gap-2 flex-wrap">
										{#each adventure.images as _, i}
											<button
												on:click={() => goToSlide(i)}
												class="btn btn-circle btn-xs transition-all duration-200"
												class:btn-primary={i === currentSlide}
												class:btn-outline={i !== currentSlide}
												class:opacity-50={i !== currentSlide}
											>
												{i + 1}
											</button>
										{/each}
									</div>
								{:else}
									<!-- Scrollable navigation for many images -->
									<div class="relative">
										<div
											class="absolute left-0 top-0 bottom-2 w-4 bg-gradient-to-r from-black/30 to-transparent pointer-events-none"
										></div>
										<div
											class="absolute right-0 top-0 bottom-2 w-4 bg-gradient-to-l from-black/30 to-transparent pointer-events-none"
										></div>
									</div>
								{/if}
							</div>
						{/if}
					</div>
				</div>
			</div>
		{:else}
			<!-- No image hero -->
			<div class="hero min-h-[40vh] bg-gradient-to-br from-primary/20 to-secondary/20">
				<div class="hero-content text-center">
					<div class="max-w-4xl">
						<h1 class="text-6xl font-bold mb-6">{adventure.name}</h1>
						{#if adventure.rating !== undefined && adventure.rating !== null}
							<div class="flex justify-center mb-6">
								<div class="rating rating-lg">
									{#each Array.from({ length: 5 }, (_, i) => i + 1) as star}
										<input
											type="radio"
											name="rating-hero-no-img"
											class="mask mask-star-2 bg-warning"
											checked={star <= adventure.rating}
											disabled
										/>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				</div>
			</div>
		{/if}
	</div>

	<!-- Main Content -->
	<div class="container mx-auto px-2 sm:px-4 py-6 sm:py-8 max-w-7xl">
		<div class="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-8">
			<!-- Left Column - Main Content -->
			<div class="lg:col-span-2 space-y-6 sm:space-y-8">
				<!-- Author Info Card -->
				{#if adventure.user}
					<div class="card bg-white">
						<div class="card-body">
							<div class="flex items-center gap-4">
								{#if adventure.user.profile_pic}
									<div class="avatar">
										<div
											class="w-16 rounded-full ring ring-primary ring-offset-base-100 ring-offset-2"
										>
											<img src={adventure.user.profile_pic} alt={adventure.user.username} />
										</div>
									</div>
								{:else}
									<div class="avatar placeholder">
										<div
											class="bg-primary text-primary-content w-16 rounded-full ring ring-primary ring-offset-base-100 ring-offset-2"
										>
											<span class="text-xl font-bold">
												{adventure.user.first_name
													? adventure.user.first_name.charAt(0)
													: adventure.user.username.charAt(0)}{adventure.user.last_name
													? adventure.user.last_name.charAt(0)
													: ''}
											</span>
										</div>
									</div>
								{/if}
								<div class="flex-1">
									<div class="text-lg font-bold">
										{#if adventure.user.public_profile}
											<a href={`/profile/${adventure.user.username}`} class="link link-hover">
												{adventure.user.first_name || adventure.user.username}
												{adventure.user.last_name || ''}
											</a>
										{:else}
											{adventure.user.first_name || adventure.user.username}
											{adventure.user.last_name || ''}
										{/if}
									</div>
									<div class="flex items-center gap-2 text-sm mt-1">
										<div
											class="badge bg-primary text-white block h-[25px] text-[14px] flex items-center"
										>
											{adventure.is_public
												? `🌍 ${$t('adventures.public')}`
												: `🔒 ${$t('adventures.private')}`}
										</div>
										<!-- {#if data.props.collection}
											<div class="badge badge-sm badge-outline">
												📚 <a href="/collections/{data.props.collection.id}" class="link"
													>{data.props.collection.name}</a
												>
											</div>
										{/if} -->
										{#if adventure.collections && adventure.collections.length > 0}
											<div class="badge badge-sm badge-outline">
												📚
												<p>{adventure.collections.length} {$t('navbar.collections')}</p>
											</div>
										{/if}
									</div>
								</div>
							</div>
						</div>
					</div>
				{/if}

				<!-- Description Card -->
				{#if adventure.description}
					<div class="card bg-white">
						<div class="card-body">
							<h2 class="card-title text-2xl mb-4">📝 {$t('adventures.description')}</h2>
							<article class="prose max-w-none">
								{@html DOMPurify.sanitize(renderMarkdown(adventure.description))}
							</article>
						</div>
					</div>
				{/if}

				<!-- Visits Timeline -->
				{#if adventure.visits.length > 0}
					<div class="card bg-white">
						<div class="card-body">
							<h2 class="card-title text-2xl mb-6">🎯 {$t('adventures.visits')}</h2>
							<div class="space-y-4">
								{#each adventure.visits as visit, index}
									<div class="flex gap-4">
										<div class="flex flex-col items-center">
											<div class="w-4 h-4 bg-primary rounded-full"></div>
											{#if index < adventure.visits.length - 1}
												<div class="w-0.5 bg-primary/30 h-full min-h-12"></div>
											{/if}
										</div>
										<div class="flex-1 pb-4">
											<div class="card bg-white">
												<div class="card-body p-4">
													{#if isAllDay(visit.start_date)}
														<div class="flex items-center gap-2 mb-2">
															<span class="badge badge-primary">All Day</span>
															<span class="font-semibold">
																{visit.start_date ? visit.start_date.split('T')[0] : ''} – {visit.end_date
																	? visit.end_date.split('T')[0]
																	: ''}
															</span>
														</div>
													{:else}
														<div class="space-y-2">
															<div class="flex items-center gap-2">
																<span class="badge badge-primary">🕓 {$t('adventures.timed')}</span>
																{#if visit.timezone}
																	<span class="badge badge-outline">{visit.timezone}</span>
																{/if}
															</div>
															<div class="text-sm">
																{#if visit.timezone}
																	<strong>{$t('adventures.start')}:</strong>
																	{DateTime.fromISO(visit.start_date, { zone: 'utc' })
																		.setZone(visit.timezone)
																		.toLocaleString(DateTime.DATETIME_MED)}<br />
																	<strong>{$t('adventures.end')}:</strong>
																	{DateTime.fromISO(visit.end_date, { zone: 'utc' })
																		.setZone(visit.timezone)
																		.toLocaleString(DateTime.DATETIME_MED)}
																{:else}
																	<strong>Start:</strong>
																	{DateTime.fromISO(visit.start_date).toLocaleString(
																		DateTime.DATETIME_MED
																	)}<br />
																	<strong>End:</strong>
																	{DateTime.fromISO(visit.end_date).toLocaleString(
																		DateTime.DATETIME_MED
																	)}
																{/if}
															</div>
														</div>
													{/if}
													{#if visit.notes}
														<div class="mt-3 p-3 bg-white-200 rounded-lg">
															<p class="text-sm italic">"{visit.notes}"</p>
														</div>
													{/if}
												</div>
											</div>
										</div>
									</div>
								{/each}
							</div>
						</div>
					</div>
				{/if}

				<!-- Map Section -->
				{#if (adventure.longitude && adventure.latitude) || geojson}
					<div class="card bg-white">
						<div class="card-body">
							<h2 class="card-title text-2xl mb-4">🗺️ {$t('adventures.location')}</h2>

							{#if adventure.longitude && adventure.latitude}
								<!-- Compact Coordinates Card -->
								<div
									class="card bg-gradient-to-br from-primary/5 to-secondary/5 mb-4 border border-primary/10"
								>
									<div class="card-body p-4">
										<div class="flex items-center justify-between mb-3">
											<h3 class="text-lg font-bold flex items-center gap-2">
												🎯 {$t('adventures.coordinates')}
											</h3>
										</div>

										<div class="grid grid-cols-2 gap-3 mb-4">
											<div class="text-center p-2 bg-white-200/70 rounded border border-primary/10">
												<div class="text-xs text-primary/70 uppercase tracking-wide">
													{$t('adventures.latitude')}
												</div>
												<div class="text-lg font-bold text-primary">{adventure.latitude}°</div>
											</div>
											<div
												class="text-center p-2 bg-white-200/70 rounded border border-secondary/10"
											>
												<div class="text-xs text-secondary/70 uppercase tracking-wide">
													{$t('adventures.longitude')}
												</div>
												<div class="text-lg font-bold text-secondary">{adventure.longitude}°</div>
											</div>
										</div>

										<!-- Location Info (individual clickable items) -->
										{#if adventure.city || adventure.region || adventure.country}
											<div class="flex flex-wrap justify-center gap-2 mb-4">
												{#if adventure.city}
													<button
														class="btn btn-xs btn-outline hover:btn-info"
														on:click={() => {
															if (adventure.country && adventure.region) {
																goto(
																	`/worldtravel/${adventure.country.country_code}/${adventure.region.id}`
																);
															} else if (adventure.country) {
																goto(`/worldtravel/${adventure.country.country_code}`);
															}
														}}
													>
														🏙️ {adventure.city.name}
													</button>
												{/if}
												{#if adventure.region}
													<button
														class="btn btn-xs btn-outline hover:btn-warning"
														on:click={() => {
															if (adventure.country && adventure.region) {
																goto(
																	`/worldtravel/${adventure.country.country_code}/${adventure.region.id}`
																);
															} else if (adventure.country) {
																goto(`/worldtravel/${adventure.country.country_code}`);
															}
														}}
													>
														🗺️ {adventure.region.name}
													</button>
												{/if}
												{#if adventure.country}
													<button
														class="btn btn-xs btn-outline hover:btn-success"
														on:click={() => goto(`/worldtravel/${adventure.country?.country_code}`)}
													>
														🌎 {adventure.country.name}
													</button>
												{/if}
											</div>
										{/if}

										<!-- External Maps Links -->
										<div class="grid grid-cols-3 gap-2 mb-3">
											<a
												class="btn btn-sm btn-outline hover:btn-neutral"
												href={`https://maps.apple.com/?q=${adventure.latitude},${adventure.longitude}`}
												target="_blank"
												rel="noopener noreferrer"
											>
												🍎 Apple
											</a>
											<a
												class="btn btn-sm btn-outline hover:btn-accent"
												href={`https://maps.google.com/?q=${adventure.latitude},${adventure.longitude}`}
												target="_blank"
												rel="noopener noreferrer"
											>
												🌍 Google
											</a>
											<a
												class="btn btn-sm btn-outline hover:btn-primary"
												href={`https://www.openstreetmap.org/?mlat=${adventure.latitude}&mlon=${adventure.longitude}`}
												target="_blank"
												rel="noopener noreferrer"
											>
												🗺️ OSM
											</a>
										</div>

										<!-- Quick Copy Actions -->
										<div class="flex gap-2">
											<button
												class="btn btn-xs btn-ghost flex-1 text-xs"
												on:click={() =>
													navigator.clipboard.writeText(
														`${adventure.latitude}, ${adventure.longitude}`
													)}
											>
												📋 {$t('adventures.copy_coordinates')}
											</button>
											<button
												class="btn btn-xs btn-ghost flex-1 text-xs"
												on:click={() =>
													navigator.clipboard.writeText(
														`https://www.google.com/maps/@${adventure.latitude},${adventure.longitude},15z`
													)}
											>
												🔗 {$t('adventures.copy_link')}
											</button>
										</div>
									</div>
								</div>
							{/if}

							<div class="rounded-lg overflow-hidden">
								<MapLibre
									style={getBasemapUrl()}
									class="w-full h-96"
									standardControls
									center={{ lng: adventure.longitude || 0, lat: adventure.latitude || 0 }}
									zoom={adventure.longitude ? 12 : 1}
								>
									{#if geojson}
										<GeoJSON data={geojson}>
											<LineLayer
												paint={{
													'line-color': '#FF0000',
													'line-width': 4
												}}
											/>
										</GeoJSON>
									{/if}

									{#if adventure.longitude && adventure.latitude}
										<DefaultMarker lngLat={{ lng: adventure.longitude, lat: adventure.latitude }}>
											<Popup openOn="click" offset={[0, -10]}>
												<div class="p-2">
													<div class="text-lg font-bold text-black mb-1">{adventure.name}</div>
													<p class="font-semibold text-black text-sm mb-2">
														{adventure.category?.display_name + ' ' + adventure.category?.icon}
													</p>
													{#if adventure.visits.length > 0}
														<div class="text-xs text-black">
															{adventure.visits.length}
															{$t('adventures.visit')}{adventure.visits.length !== 1 ? 's' : ''}
														</div>
													{/if}
												</div>
											</Popup>
										</DefaultMarker>
									{/if}
								</MapLibre>
							</div>
						</div>
					</div>
				{/if}
			</div>

			<!-- Right Column - Sidebar -->
			<div class="space-y-4 sm:space-y-6">
				<!-- Quick Info Card -->
				<div class="card bg-white">
					<div class="card-body">
						<h3 class="card-title text-lg mb-4">ℹ️ {$t('adventures.basic_information')}</h3>
						<div class="space-y-3">
							{#if adventure.activity_types && adventure.activity_types?.length > 0}
								<div>
									<div class="text-sm opacity-70 mb-1">{$t('adventures.tags')}</div>
									<div class="flex flex-wrap gap-1">
										{#each adventure.activity_types as activity}
											<span class="badge badge-sm badge-outline">{activity}</span>
										{/each}
									</div>
								</div>
							{/if}
							{#if adventure.link}
								<div>
									<div class="text-sm opacity-70 mb-1">{$t('adventures.link')}</div>
									<a
										href={adventure.link}
										class="link link-primary text-sm break-all"
										target="_blank"
									>
										{adventure.link.length > 30
											? `${adventure.link.slice(0, 30)}...`
											: adventure.link}
									</a>
								</div>
							{/if}
						</div>
					</div>
				</div>

				<!-- Sunrise/Sunset -->
				{#if adventure.sun_times && adventure.sun_times.length > 0}
					<div class="card bg-white">
						<div class="card-body">
							<h3 class="card-title text-lg mb-4">
								🌅 {$t('adventures.sun_times')}
								<WeatherSunset class="w-5 h-5" />
							</h3>
							<div class="space-y-3">
								{#each adventure.sun_times as sun_time}
									<div class="border-l-4 border-warning pl-3">
										<div class="font-semibold text-sm">
											{new Date(sun_time.date).toLocaleDateString()}
										</div>
										<div class="text-xs opacity-70">
											{$t('adventures.sunrise')}: {sun_time.sunrise} • {$t('adventures.sunset')}: {sun_time.sunset}
										</div>
									</div>
								{/each}
							</div>
						</div>
					</div>
				{/if}

				<!-- Attachments -->
				{#if adventure.attachments && adventure.attachments.length > 0}
					<div class="card bg-white">
						<div class="card-body">
							<h3 class="card-title text-lg mb-4">
								📎 {$t('adventures.attachments')}
								<div class="tooltip" data-tip={$t('adventures.gpx_tip')}>
									<LightbulbOn class="w-4 h-4 opacity-60" />
								</div>
							</h3>
							<div class="space-y-2">
								{#each adventure.attachments as attachment}
									<AttachmentCard {attachment} />
								{/each}
							</div>
						</div>
					</div>
				{/if}

				<!-- Additional Images -->
				{#if adventure.images && adventure.images.length > 1}
					<div class="card bg-white">
						<div class="card-body">
							<h3 class="card-title text-lg mb-4">🖼️ {$t('adventures.images')}</h3>
							<div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
								{#each adventure.images as image}
									<div class="relative group">
										<div
											class="aspect-square bg-cover bg-center rounded-lg cursor-pointer transition-transform duration-200 group-hover:scale-105"
											style="background-image: url({image.image})"
											on:click={() => (image_url = image.image)}
											on:keydown={(e) => e.key === 'Enter' && (image_url = image.image)}
											role="button"
											tabindex="0"
										></div>
										{#if image.is_primary}
											<div class="absolute top-1 right-1">
												<span class="badge badge-primary badge-xs">{$t('settings.primary')}</span>
											</div>
										{/if}
									</div>
								{/each}
							</div>
						</div>
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}

<svelte:head>
	<title>
		{data.props.adventure && data.props.adventure.name
			? `${data.props.adventure.name}`
			: 'Adventure'}
	</title>
	<meta name="description" content="Explore the world and add countries to your visited list!" />
</svelte:head>
