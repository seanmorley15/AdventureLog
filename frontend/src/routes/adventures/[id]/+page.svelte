<script lang="ts">
	import type { AdditionalAdventure, Adventure } from '$lib/types';
	import { onMount } from 'svelte';
	import type { PageData } from './$types';
	import { goto } from '$app/navigation';
	import Lost from '$lib/assets/undraw_lost.svg';
	import { DefaultMarker, MapLibre, Popup, GeoJSON, LineLayer } from 'svelte-maplibre';
	import { t } from 'svelte-i18n';
	import { marked } from 'marked'; // Import the markdown parser
	import DOMPurify from 'dompurify';
	// @ts-ignore
	import toGeoJSON from '@mapbox/togeojson';

	import LightbulbOn from '~icons/mdi/lightbulb-on';
	import WeatherSunset from '~icons/mdi/weather-sunset';

	let geojson: any;

	const renderMarkdown = (markdown: string) => {
		return marked(markdown) as string;
	};

	async function getGpxFiles() {
		let gpxfiles: string[] = [];

		// Collect all GPX file attachments
		if (adventure.attachments && adventure.attachments.length > 0) {
			gpxfiles = adventure.attachments
				.filter((attachment) => attachment.extension === 'gpx')
				.map((attachment) => attachment.file);
		}

		// Initialize the GeoJSON collection
		geojson = {
			type: 'FeatureCollection',
			features: []
		};

		// Process each GPX file concurrently
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

					// Convert GPX to GeoJSON and return features
					const convertedGeoJSON = toGeoJSON.gpx(gpx);
					return convertedGeoJSON.features || [];
				} catch (error) {
					console.error(`Error processing GPX file ${gpxfile}:`, error);
					return [];
				}
			});

			// Use Promise.allSettled to ensure every promise resolves,
			// even if some requests fail.
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

	import ClipboardList from '~icons/mdi/clipboard-list';
	import AdventureModal from '$lib/components/AdventureModal.svelte';
	import ImageDisplayModal from '$lib/components/ImageDisplayModal.svelte';
	import AttachmentCard from '$lib/components/AttachmentCard.svelte';
	import { isAllDay } from '$lib';

	onMount(async () => {
		if (data.props.adventure) {
			adventure = data.props.adventure;
			// sort so that any image in adventure_images .is_primary is first
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
	<div
		class="flex min-h-[100dvh] flex-col items-center justify-center bg-background px-4 py-12 sm:px-6 lg:px-8 -mt-20"
	>
		<div class="mx-auto max-w-md text-center">
			<div class="flex items-center justify-center">
				<img src={Lost} alt="Lost" class="w-1/2" />
			</div>
			<h1 class="mt-4 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
				{$t('adventures.not_found')}
			</h1>
			<p class="mt-4 text-muted-foreground">
				{$t('adventures.not_found_desc')}
			</p>
			<div class="mt-6">
				<button class="btn btn-primary" on:click={() => goto('/')}
					>{$t('adventures.homepage')}</button
				>
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
	<div class="flex justify-center items-center w-full mt-16">
		<span class="loading loading-spinner w-24 h-24"></span>
	</div>
{/if}

{#if adventure}
	{#if data.user && data.user.uuid == adventure.user_id}
		<div class="fixed bottom-4 right-4 z-[999]">
			<button class="btn m-1 size-16 btn-primary" on:click={() => (isEditModalOpen = true)}
				><ClipboardList class="w-8 h-8" /></button
			>
		</div>
	{/if}
	<div class="flex flex-col min-h-dvh">
		<main class="flex-1">
			<div class="max-w-5xl mx-auto p-4 md:p-6 lg:p-8">
				<div class="grid gap-8">
					{#if adventure.images && adventure.images.length > 0}
						<div class="carousel w-full">
							{#each adventure.images as image, i}
								<!-- svelte-ignore a11y-no-static-element-interactions -->
								<!-- svelte-ignore a11y-missing-attribute -->
								<!-- svelte-ignore a11y-missing-content -->
								<div
									class="carousel-item w-full"
									style="display: {i === currentSlide ? 'block' : 'none'}"
								>
									<!-- svelte-ignore a11y-click-events-have-key-events -->
									<!-- svelte-ignore a11y-missing-attribute -->
									<a on:click={() => (image_url = image.image)}>
										<img
											src={image.image}
											width="1200"
											height="600"
											class="w-full h-auto object-cover rounded-lg"
											style="aspect-ratio: 1200 / 600; object-fit: cover;"
											alt={adventure.name}
										/>
									</a>
									<!-- Scrollable button container -->
									<div
										class="flex w-full py-2 gap-2 overflow-x-auto whitespace-nowrap scrollbar-hide justify-start"
									>
										{#each adventure.images as _, i}
											<button
												on:click={() => goToSlide(i)}
												class="btn btn-xs {i === currentSlide ? 'btn-active' : ''}">{i + 1}</button
											>
										{/each}
									</div>
								</div>
							{/each}
						</div>
					{/if}

					<div class="grid gap-4">
						<div class="flex items-center justify-between">
							<div>
								<h1 class="text-4xl mt-2 font-bold">{adventure.name}</h1>
							</div>
							<div class="flex items-center gap-1">
								{#if adventure.rating !== undefined && adventure.rating !== null}
									<div class="flex justify-center items-center">
										<div class="rating" aria-readonly="true">
											{#each Array.from({ length: 5 }, (_, i) => i + 1) as star}
												<input
													type="radio"
													name="rating-1"
													class="mask mask-star"
													checked={star <= adventure.rating}
													disabled
												/>
											{/each}
										</div>
									</div>
								{/if}
							</div>
						</div>
						<div class="grid gap-2">
							{#if adventure.user}
								<div class="flex items-center gap-2">
									{#if adventure.user.profile_pic}
										<div class="avatar">
											<div class="w-8 rounded-full">
												<img src={adventure.user.profile_pic} alt={adventure.user.username} />
											</div>
										</div>
									{:else}
										<div class="avatar placeholder">
											<div class="bg-neutral text-neutral-content w-8 rounded-full">
												<span class="text-lg"
													>{adventure.user.first_name
														? adventure.user.first_name.charAt(0)
														: adventure.user.username.charAt(0)}{adventure.user.last_name
														? adventure.user.last_name.charAt(0)
														: ''}</span
												>
											</div>
										</div>
									{/if}

									<div>
										{#if adventure.user.public_profile}
											<a href={`/profile/${adventure.user.username}`} class="text-base font-medium">
												{adventure.user.first_name || adventure.user.username}{' '}
												{adventure.user.last_name}
											</a>
										{:else}
											<span class="text-base font-medium">
												{adventure.user.first_name || adventure.user.username}{' '}
												{adventure.user.last_name}
											</span>
										{/if}
									</div>
								</div>
							{/if}
							<div class="flex items-center gap-2">
								<svg
									xmlns="http://www.w3.org/2000/svg"
									width="24"
									height="24"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
									stroke-linecap="round"
									stroke-linejoin="round"
									class="w-5 h-5 text-muted-foreground"
								>
									<rect width="18" height="11" x="3" y="11" rx="2" ry="2"></rect>
									<path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
								</svg>
								<span class="text-sm text-muted-foreground"
									>{adventure.is_public ? 'Public' : 'Private'}</span
								>
							</div>

							{#if adventure.location}
								<div class="flex items-center gap-2">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										width="24"
										height="24"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
										stroke-linecap="round"
										stroke-linejoin="round"
										class="w-5 h-5 text-muted-foreground"
									>
										<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"></path>
										<circle cx="12" cy="10" r="3"></circle>
									</svg>
									<span class="text-sm text-muted-foreground">{adventure.location}</span>
								</div>
							{/if}
							{#if adventure.activity_types && adventure.activity_types?.length > 0}
								<div class="flex items-center gap-2">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										width="24"
										height="24"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
										stroke-linecap="round"
										stroke-linejoin="round"
										class="w-5 h-5 text-muted-foreground"
									>
										<path
											d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"
										></path>
									</svg>
									<span class="text-sm text-muted-foreground"
										>{adventure.activity_types.join(', ')}</span
									>
								</div>
							{/if}
							{#if adventure.link}
								<div class="flex items-center gap-2">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										width="24"
										height="24"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
										stroke-linecap="round"
										stroke-linejoin="round"
										class="w-5 h-5 text-muted-foreground"
									>
										<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
										<path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
									</svg>
									<a
										href={adventure.link}
										class="text-sm text-muted-foreground hover:underline"
										target="_blank"
									>
										{adventure.link.length > 45
											? `${adventure.link.slice(0, 45)}...`
											: adventure.link}
									</a>
								</div>
							{/if}
						</div>
						{#if adventure.description}
							<p class="text-sm text-muted-foreground" style="white-space: pre-wrap;"></p>
							<article
								class="prose overflow-auto h-full max-w-full p-4 border border-base-300 rounded-lg"
							>
								{@html DOMPurify.sanitize(renderMarkdown(adventure.description))}
							</article>
						{/if}
					</div>
				</div>
				<div
					data-orientation="horizontal"
					role="none"
					class="shrink-0 bg-border h-[1px] w-full my-8"
				></div>
				<div class="grid gap-8">
					<div>
						<h2 class="text-2xl font-bold mt-4">{$t('adventures.adventure_details')}</h2>
						<div class="grid gap-4 mt-4">
							<div class="grid md:grid-cols-2 gap-4">
								<div>
									<p class="text-sm text-muted-foreground">{$t('adventures.adventure_type')}</p>
									<p class="text-base font-medium">
										{adventure.category?.display_name + ' ' + adventure.category?.icon}
									</p>
								</div>
								{#if data.props.collection}
									<div>
										<p class="text-sm text-muted-foreground">{$t('adventures.collection')}</p>
										<a
											class="text-base font-medium link"
											href="/collections/{data.props.collection.id}">{data.props.collection.name}</a
										>
									</div>
								{/if}
								{#if adventure.visits.length > 0}
									<div>
										<p class="text-sm text-muted-foreground">Visits</p>
										<p class="text-base font-medium">
											{adventure.visits.length}
											{adventure.visits.length > 1
												? $t('adventures.visits')
												: $t('adventures.visit') + ':'}
										</p>
										<!-- show each visit start and end date as well as notes -->
										{#each adventure.visits as visit}
											<div class="flex flex-col gap-2">
												<div class="flex gap-2 items-center">
													<p>
														{#if isAllDay(visit.start_date)}
															<!-- For all-day events, show just the date -->
															{new Date(visit.start_date).toLocaleDateString(undefined, {
																timeZone: 'UTC'
															})}
														{:else}
															<!-- For timed events, show date and time -->
															{new Date(visit.start_date).toLocaleDateString()} ({new Date(
																visit.start_date
															).toLocaleTimeString()})
														{/if}
													</p>
													{#if visit.end_date && visit.end_date !== visit.start_date}
														<p>
															- {new Date(visit.end_date).toLocaleDateString(undefined, {
																timeZone: 'UTC'
															})}
															{#if !isAllDay(visit.end_date)}
																({new Date(visit.end_date).toLocaleTimeString()})
															{/if}
														</p>
													{/if}
												</div>
												<p class="whitespace-pre-wrap -mt-2 mb-2">{visit.notes}</p>
											</div>
										{/each}
									</div>
								{/if}
							</div>
							{#if (adventure.longitude && adventure.latitude) || geojson}
								{#if adventure.longitude && adventure.latitude}
									<div class="grid md:grid-cols-2 gap-4">
										<div>
											<p class="text-sm text-muted-foreground">{$t('adventures.latitude')}</p>
											<p class="text-base font-medium">{adventure.latitude}° N</p>
										</div>
										<div>
											<p class="text-sm text-muted-foreground">{$t('adventures.longitude')}</p>
											<p class="text-base font-medium">{adventure.longitude}° W</p>
										</div>
									</div>
								{/if}
								{#if adventure.longitude && adventure.latitude}
									<div>
										<p class="mb-1">{$t('adventures.open_in_maps')}:</p>
										<div class="flex flex-wrap gap-2">
											<a
												class="btn btn-neutral text-base btn-sm max-w-32"
												href={`https://maps.apple.com/?q=${adventure.latitude},${adventure.longitude}`}
												target="_blank"
												rel="noopener noreferrer">Apple</a
											>
											<a
												class="btn btn-neutral text-base btn-sm max-w-32"
												href={`https://maps.google.com/?q=${adventure.latitude},${adventure.longitude}`}
												target="_blank"
												rel="noopener noreferrer">Google</a
											>
											<a
												class="btn btn-neutral text-base btn-sm max-w-32"
												href={`https://www.openstreetmap.org/?mlat=${adventure.latitude}&mlon=${adventure.longitude}`}
												target="_blank"
												rel="noopener noreferrer">OSM</a
											>
										</div>
									</div>
								{/if}
								<MapLibre
									style="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
									class="flex items-center self-center justify-center aspect-[9/16] max-h-[70vh] sm:aspect-video sm:max-h-full w-10/12 rounded-lg"
									standardControls
									center={{ lng: adventure.longitude || 0, lat: adventure.latitude || 0 }}
									zoom={adventure.longitude ? 12 : 1}
								>
									<!-- use the geojson to make a line -->
									{#if geojson}
										<!-- Add the GeoJSON data -->
										<GeoJSON data={geojson}>
											<LineLayer
												paint={{
													'line-color': '#FF0000', // Red line color
													'line-width': 4 // Adjust the line thickness
												}}
											/>
										</GeoJSON>
									{/if}

									<!-- MapEvents gives you access to map events even from other components inside the map,
  where you might not have access to the top-level `MapLibre` component. In this case
  it would also work to just use on:click on the MapLibre component itself. -->
									<!-- <MapEvents on:click={addMarker} /> -->

									{#if adventure.longitude && adventure.latitude}
										<DefaultMarker lngLat={{ lng: adventure.longitude, lat: adventure.latitude }}>
											<Popup openOn="click" offset={[0, -10]}>
												<div class="text-lg text-black font-bold">{adventure.name}</div>
												<p class="font-semibold text-black text-md">
													{adventure.category?.display_name + ' ' + adventure.category?.icon}
												</p>
												{#if adventure.visits.length > 0}
													<p>
														{#each adventure.visits as visit}
															<div
																class="p-4 border border-neutral rounded-lg bg-base-100 shadow-sm flex flex-col gap-2"
															>
																<p class="text-sm text-base-content font-medium">
																	{#if isAllDay(visit.start_date)}
																		<span class="badge badge-outline mr-2">All Day</span>
																		{visit.start_date.split('T')[0]} – {visit.end_date.split(
																			'T'
																		)[0]}
																	{:else}
																		{new Date(visit.start_date).toLocaleString()} – {new Date(
																			visit.end_date
																		).toLocaleString()}
																	{/if}
																</p>

																<!-- If the selected timezone is not the current one show the timezone + the time converted there -->

																{#if visit.notes}
																	<p class="text-sm text-base-content opacity-70 italic">
																		"{visit.notes}"
																	</p>
																{/if}
															</div>
														{/each}
													</p>
												{/if}
											</Popup>
										</DefaultMarker>
									{/if}
								</MapLibre>
							{/if}
						</div>

						<!-- Additional Info Display Section -->

						<div>
							{#if adventure.sun_times && adventure.sun_times.length > 0}
								<h2 class="text-2xl font-bold mt-4 mb-4">{$t('adventures.additional_info')}</h2>
								{#if adventure.sun_times && adventure.sun_times.length > 0}
									<div class="collapse collapse-plus bg-base-200 mb-2 overflow-visible">
										<input type="checkbox" />
										<div class="collapse-title text-xl font-medium">
											<span>
												{$t('adventures.sunrise_sunset')}
												<WeatherSunset class="w-6 h-6 inline-block ml-2 -mt-1" />
											</span>
										</div>

										<div class="collapse-content">
											<div class="grid gap-4 mt-4">
												<!-- Sunrise and Sunset times -->
												{#each adventure.sun_times as sun_time}
													<div class="grid md:grid-cols-3 gap-4">
														<div>
															<p class="text-sm text-muted-foreground">Date</p>
															<p class="text-base font-medium">
																{new Date(sun_time.date).toLocaleDateString()}
															</p>
														</div>
														<div>
															<p class="text-sm text-muted-foreground">Sunrise</p>
															<p class="text-base font-medium">
																{sun_time.sunrise}
															</p>
														</div>
														<div>
															<p class="text-sm text-muted-foreground">Sunset</p>
															<p class="text-base font-medium">
																{sun_time.sunset}
															</p>
														</div>
													</div>
												{/each}
											</div>
										</div>
									</div>
								{/if}
							{/if}

							{#if adventure.attachments && adventure.attachments.length > 0}
								<div>
									<!-- attachments -->
									<h2 class="text-2xl font-bold mt-4">
										{$t('adventures.attachments')}
										<div class="tooltip z-10" data-tip={$t('adventures.gpx_tip')}>
											<button class="btn btn-sm btn-circle btn-neutral">
												<LightbulbOn class="w-6 h-6" />
											</button>
										</div>
									</h2>

									<div class="grid gap-4 mt-4">
										{#if adventure.attachments && adventure.attachments.length > 0}
											<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
												{#each adventure.attachments as attachment}
													<AttachmentCard {attachment} />
												{/each}
											</div>
										{/if}
									</div>
								</div>
							{/if}
							{#if adventure.images && adventure.images.length > 0}
								<div>
									<h2 class="text-2xl font-bold mt-4">{$t('adventures.images')}</h2>
									<div class="grid gap-4 mt-4">
										{#if adventure.images && adventure.images.length > 0}
											<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
												{#each adventure.images as image}
													<div class="relative">
														<!-- svelte-ignore a11y-no-static-element-interactions -->
														<!-- svelte-ignore a11y-missing-attribute -->
														<!-- svelte-ignore a11y-missing-content -->
														<!-- svelte-ignore a11y-click-events-have-key-events -->
														<div
															class="w-full h-48 bg-cover bg-center rounded-lg"
															style="background-image: url({image.image})"
															on:click={() => (image_url = image.image)}
														></div>
														{#if image.is_primary}
															<div
																class="absolute top-0 right-0 bg-primary text-white px-2 py-1 rounded-bl-lg"
															>
																{$t('adventures.primary')}
															</div>
														{/if}
													</div>
												{/each}
											</div>
										{/if}
									</div>
								</div>
							{/if}
						</div>
					</div>
				</div>
			</div>
		</main>
	</div>
{/if}

<svelte:head>
	<title
		>{data.props.adventure && data.props.adventure.name
			? `${data.props.adventure.name}`
			: 'Adventure'}</title
	>
	<meta name="description" content="Explore the world and add countries to your visited list!" />
</svelte:head>
