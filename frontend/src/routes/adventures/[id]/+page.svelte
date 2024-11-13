<script lang="ts">
	import type { Adventure } from '$lib/types';
	import { onMount } from 'svelte';
	import type { PageData } from './$types';
	import { goto } from '$app/navigation';
	import Lost from '$lib/assets/undraw_lost.svg';
	import { DefaultMarker, MapLibre, Popup } from 'svelte-maplibre';
	import { t } from 'svelte-i18n';

	export let data: PageData;
	console.log(data);

	let adventure: Adventure;

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

	onMount(() => {
		if (data.props.adventure) {
			adventure = data.props.adventure;
		} else {
			notFound = true;
		}
	});

	function saveEdit(event: CustomEvent<Adventure>) {
		adventure = event.detail;
		isEditModalOpen = false;
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
	{#if data.user && data.user.pk == adventure.user_id}
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
									<div class="flex justify-center w-full py-2 gap-2">
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
							<div class="grid gap-2">
								<p class="text-sm text-muted-foreground" style="white-space: pre-wrap;">
									{adventure.description}
								</p>
							</div>
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
										{$t(`adventures.activities.${adventure.type}`)}
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
											<div class="grid gap-2">
												<p class="text-sm text-muted-foreground">
													{visit.start_date
														? new Date(visit.start_date).toLocaleDateString(undefined, {
																timeZone: 'UTC'
															})
														: ''}
													{visit.end_date &&
													visit.end_date !== '' &&
													visit.end_date !== visit.start_date
														? ' - ' +
															new Date(visit.end_date).toLocaleDateString(undefined, {
																timeZone: 'UTC'
															})
														: ''}
												</p>
												<p class="text-sm text-muted-foreground -mt-2 mb-2">{visit.notes}</p>
											</div>
										{/each}
									</div>
								{/if}
							</div>
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
								<MapLibre
									style="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
									class="flex items-center self-center justify-center aspect-[9/16] max-h-[70vh] sm:aspect-video sm:max-h-full w-10/12"
									standardControls
									center={{ lng: adventure.longitude, lat: adventure.latitude }}
									zoom={12}
								>
									<!-- MapEvents gives you access to map events even from other components inside the map,
  where you might not have access to the top-level `MapLibre` component. In this case
  it would also work to just use on:click on the MapLibre component itself. -->
									<!-- <MapEvents on:click={addMarker} /> -->

									<DefaultMarker lngLat={{ lng: adventure.longitude, lat: adventure.latitude }}>
										<Popup openOn="click" offset={[0, -10]}>
											<div class="text-lg text-black font-bold">{adventure.name}</div>
											<p class="font-semibold text-black text-md">
												{adventure.type.charAt(0).toUpperCase() + adventure.type.slice(1)}
											</p>
											{#if adventure.visits.length > 0}
												<p class="text-black text-sm">
													{#each adventure.visits as visit}
														{visit.start_date
															? new Date(visit.start_date).toLocaleDateString(undefined, {
																	timeZone: 'UTC'
																})
															: ''}
														{visit.end_date &&
														visit.end_date !== '' &&
														visit.end_date !== visit.start_date
															? ' - ' +
																new Date(visit.end_date).toLocaleDateString(undefined, {
																	timeZone: 'UTC'
																})
															: ''}
														<br />
													{/each}
												</p>
											{/if}
										</Popup>
									</DefaultMarker>
								</MapLibre>
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
