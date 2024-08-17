<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { Adventure, OpenStreetMapPlace, Point } from '$lib/types';
	import { onMount } from 'svelte';
	import { enhance } from '$app/forms';
	import { addToast } from '$lib/toasts';

	export let type: string = 'visited';

	export let longitude: number | null = null;
	export let latitude: number | null = null;
	export let collection_id: string | null = null;

	import { DefaultMarker, MapEvents, MapLibre } from 'svelte-maplibre';
	let markers: Point[] = [];
	let query: string = '';
	let places: OpenStreetMapPlace[] = [];
	let images: { id: string; image: string }[] = [];

	import Earth from '~icons/mdi/earth';
	import ActivityComplete from './ActivityComplete.svelte';
	import { appVersion } from '$lib/config';

	export let startDate: string | null = null;
	export let endDate: string | null = null;

	let noPlaces: boolean = false;
	let wikiError: string = '';

	let newAdventure: Adventure = {
		id: '',
		type: type,
		name: '',
		location: null,
		date: null,
		description: '',
		activity_types: [],
		rating: NaN,
		link: '',
		images: [],
		user_id: NaN,
		latitude: null,
		longitude: null,
		is_public: false,
		collection: collection_id || ''
	};

	if (longitude && latitude) {
		newAdventure.latitude = latitude;
		newAdventure.longitude = longitude;
		reverseGeocode();
	}

	function saveAndClose() {
		dispatch('create', newAdventure);
		close();
	}

	$: if (markers.length > 0) {
		newAdventure.latitude = Math.round(markers[0].lngLat.lat * 1e6) / 1e6;
		newAdventure.longitude = Math.round(markers[0].lngLat.lng * 1e6) / 1e6;
		// if (!newAdventure.location) {
		newAdventure.location = markers[0].location;
		// }

		newAdventure.name = markers[0].name;
	}

	async function geocode(e: Event | null) {
		if (e) {
			e.preventDefault();
		}
		if (!query) {
			alert('Please enter a location');
			return;
		}
		let res = await fetch(`https://nominatim.openstreetmap.org/search?q=${query}&format=jsonv2`, {
			headers: {
				'User-Agent': `AdventureLog / ${appVersion} `
			}
		});
		console.log(res);
		let data = (await res.json()) as OpenStreetMapPlace[];
		places = data;

		if (data.length === 0) {
			noPlaces = true;
		} else {
			noPlaces = false;
		}
	}

	async function reverseGeocode() {
		let res = await fetch(
			`https://nominatim.openstreetmap.org/search?q=${newAdventure.latitude},${newAdventure.longitude}&format=jsonv2`,
			{
				headers: {
					'User-Agent': `AdventureLog / ${appVersion} `
				}
			}
		);
		let data = (await res.json()) as OpenStreetMapPlace[];
		if (data.length > 0) {
			newAdventure.name = data[0]?.name || '';
			newAdventure.activity_types?.push(data[0]?.type || '');
			newAdventure.location = data[0]?.display_name || '';
		}
		console.log(data);
	}

	let fileInput: HTMLInputElement;

	const dispatch = createEventDispatcher();
	let modal: HTMLDialogElement;

	onMount(async () => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}
	});

	function close() {
		dispatch('close');
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			close();
		}
	}

	async function generateDesc() {
		let res = await fetch(`/api/generate/desc/?name=${newAdventure.name}`);
		let data = await res.json();
		if (data.extract && data.extract.length > 0) {
			newAdventure.description = data.extract;
			wikiError = '';
		} else {
			wikiError = 'No description found';
		}
	}

	function addMarker(e: CustomEvent<any>) {
		markers = [];
		markers = [...markers, { lngLat: e.detail.lngLat, name: '', location: '', activity_type: '' }];
		console.log(markers);
	}

	function imageSubmit() {
		return async ({ result }: any) => {
			if (result.type === 'success') {
				if (result.data.id && result.data.image) {
					newAdventure.images = [...newAdventure.images, result.data];
					images = [...images, result.data];
					addToast('success', 'Image uploaded');

					fileInput.value = '';
					console.log(newAdventure);
				} else {
					addToast('error', result.data.error || 'Failed to upload image');
				}
			}
		};
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();
		console.log(newAdventure);
		let res = await fetch('/api/adventures/', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(newAdventure)
		});
		let data = await res.json();
		if (data.id) {
			newAdventure = data as Adventure;
		} else {
			addToast('error', 'Failed to create adventure');
		}
	}
</script>

<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
<dialog id="my_modal_1" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div class="modal-box w-11/12 max-w-2xl" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<h3 class="font-bold text-lg">New {newAdventure.type} Adventure</h3>
		{#if newAdventure.id === ''}
			<div class="modal-action items-center">
				<form
					method="post"
					style="width: 100%;"
					on:submit={handleSubmit}
					action="/adventures/create"
				>
					<!-- Grid layout for form fields -->
					<h2 class="text-2xl font-semibold mb-2">Basic Information</h2>
					<!-- <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3"> -->
					<div>
						<label for="name">Name</label><br />
						<input
							type="text"
							id="name"
							name="name"
							bind:value={newAdventure.name}
							class="input input-bordered w-full"
							required
						/>
					</div>
					<div>
						<div class="form-control">
							<label class="label cursor-pointer">
								<span class="label-text">Visited</span>
								<input
									type="radio"
									name="radio-10"
									class="radio checked:bg-red-500"
									on:click={() => (newAdventure.type = 'visited')}
									checked={newAdventure.type == 'visited'}
								/>
							</label>
						</div>
						<div class="form-control">
							<label class="label cursor-pointer">
								<span class="label-text">Planned</span>
								<input
									type="radio"
									name="radio-10"
									class="radio checked:bg-blue-500"
									on:click={() => (newAdventure.type = 'planned')}
									checked={newAdventure.type == 'planned'}
								/>
							</label>
						</div>
					</div>

					<div>
						<label for="date">Date</label><br />
						<input
							type="date"
							id="date"
							name="date"
							min={startDate || ''}
							max={endDate || ''}
							bind:value={newAdventure.date}
							class="input input-bordered w-full"
						/>
					</div>
					<div>
						<label for="description">Description</label><br />
						<textarea
							id="description"
							name="description"
							bind:value={newAdventure.description}
							class="textarea textarea-bordered w-full h-32"
						></textarea>
						<button class="btn btn-neutral" type="button" on:click={generateDesc}
							>Search Wikipedia</button
						>
						<p class="text-red-500">{wikiError}</p>
					</div>
					<div>
						<label for="activity_types">Activity Types</label><br />
						<input
							type="text"
							id="activity_types"
							name="activity_types"
							hidden
							bind:value={newAdventure.activity_types}
							class="input input-bordered w-full"
						/>
						<ActivityComplete bind:activities={newAdventure.activity_types} />
					</div>
					<div>
						<label for="rating"
							>Rating <iconify-icon icon="mdi:star" class="text-xl -mb-1"></iconify-icon></label
						><br />
						<input
							type="number"
							min="0"
							max="5"
							hidden
							bind:value={newAdventure.rating}
							id="rating"
							name="rating"
							class="input input-bordered w-full max-w-xs mt-1"
						/>
						<div class="rating -ml-3 mt-1">
							<input
								type="radio"
								name="rating-2"
								class="rating-hidden"
								checked={Number.isNaN(newAdventure.rating)}
							/>
							<input
								type="radio"
								name="rating-2"
								class="mask mask-star-2 bg-orange-400"
								on:click={() => (newAdventure.rating = 1)}
							/>
							<input
								type="radio"
								name="rating-2"
								class="mask mask-star-2 bg-orange-400"
								on:click={() => (newAdventure.rating = 2)}
							/>
							<input
								type="radio"
								name="rating-2"
								class="mask mask-star-2 bg-orange-400"
								on:click={() => (newAdventure.rating = 3)}
							/>
							<input
								type="radio"
								name="rating-2"
								class="mask mask-star-2 bg-orange-400"
								on:click={() => (newAdventure.rating = 4)}
							/>
							<input
								type="radio"
								name="rating-2"
								class="mask mask-star-2 bg-orange-400"
								on:click={() => (newAdventure.rating = 5)}
							/>
							{#if newAdventure.rating}
								<button
									type="button"
									class="btn btn-sm btn-error ml-2"
									on:click={() => (newAdventure.rating = NaN)}
								>
									Remove
								</button>
							{/if}
						</div>
					</div>
					<div>
						<!-- link -->
						<div>
							<label for="link">Link</label><br />
							<input
								type="text"
								id="link"
								name="link"
								bind:value={newAdventure.link}
								class="input input-bordered w-full"
							/>
						</div>
					</div>
					<div>
						<div>
							<div class="mt-2">
								<label for="is_public"
									>Public <Earth class="inline-block -mt-1 mb-1 w-6 h-6" /></label
								><br />
								<input
									type="checkbox"
									class="toggle toggle-primary"
									id="is_public"
									name="is_public"
									bind:checked={newAdventure.is_public}
								/>
							</div>
							{#if newAdventure.is_public}
								<p>
									The link to this adventure will be copied to your clipboard once it is created!
								</p>
							{/if}
						</div>
						<!-- </div> -->
					</div>
					<div class="divider"></div>
					<h2 class="text-2xl font-semibold mb-2 mt-4">Location Information</h2>
					<!-- <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3"> -->
					<div>
						<label for="latitude">Location</label><br />
						<input
							type="text"
							id="location"
							name="location"
							bind:value={newAdventure.location}
							class="input input-bordered w-full"
						/>
					</div>
					<div>
						<form on:submit={geocode} class="mt-2">
							<input
								type="text"
								placeholder="Seach for a location"
								class="input input-bordered w-full max-w-xs mb-2"
								id="search"
								name="search"
								bind:value={query}
							/>
							<button class="btn btn-neutral -mt-1" type="submit">Search</button>
						</form>
					</div>
					{#if places.length > 0}
						<div class="mt-4 max-w-full">
							<h3 class="font-bold text-lg mb-4">Search Results</h3>

							<div class="flex flex-wrap">
								{#each places as place}
									<button
										type="button"
										class="btn btn-neutral mb-2 mr-2 max-w-full break-words whitespace-normal text-left"
										on:click={() => {
											markers = [
												{
													lngLat: { lng: Number(place.lon), lat: Number(place.lat) },
													location: place.display_name,
													name: place.name,
													activity_type: place.type
												}
											];
										}}
									>
										{place.display_name}
									</button>
								{/each}
							</div>
						</div>
					{:else if noPlaces}
						<p class="text-error text-lg">No results found</p>
					{/if}
					<div>
						<MapLibre
							style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
							class="relative aspect-[9/16] max-h-[70vh] w-full sm:aspect-video sm:max-h-full"
							standardControls
						>
							<!-- MapEvents gives you access to map events even from other components inside the map,
where you might not have access to the top-level `MapLibre` component. In this case
it would also work to just use on:click on the MapLibre component itself. -->
							<MapEvents on:click={addMarker} />

							{#each markers as marker}
								<DefaultMarker lngLat={marker.lngLat} />
							{/each}
						</MapLibre>
					</div>

					<div class="mt-4">
						<button type="submit" class="btn btn-primary">Create</button>
						<button type="button" class="btn" on:click={close}>Close</button>
					</div>
				</form>
			</div>
		{:else}
			<p>Upload images here</p>
			<!-- <p>{newAdventure.id}</p> -->
			<div class="mb-2">
				<label for="image">Image </label><br />
				<div class="flex">
					<form
						method="POST"
						action="adventures?/image"
						use:enhance={imageSubmit}
						enctype="multipart/form-data"
					>
						<input
							type="file"
							name="image"
							class="file-input file-input-bordered w-full max-w-xs"
							bind:this={fileInput}
							accept="image/*"
							id="image"
						/>
						<input type="hidden" name="adventure" value={newAdventure.id} id="adventure" />
						<button class="btn btn-neutral mt-2 mb-2" type="submit">Upload Image</button>
					</form>
				</div>
				<div class=" inline-flex gap-2">
					{#each images as image}
						<img src={image.image} alt={image.id} class="w-32 h-32" />
					{/each}
				</div>
			</div>
			<div class="mt-4">
				<button type="button" class="btn btn-primary" on:click={saveAndClose}>Close</button>
			</div>
		{/if}
	</div>
</dialog>
