<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { Adventure, OpenStreetMapPlace, Point } from '$lib/types';
	import { onMount } from 'svelte';
	import { enhance } from '$app/forms';
	import { addToast } from '$lib/toasts';
	import { deserialize } from '$app/forms';

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

	let wikiError: string = '';

	let noPlaces: boolean = false;

	export let adventureToEdit: Adventure | null = null;

	let adventure: Adventure = {
		id: adventureToEdit?.id || '',
		name: adventureToEdit?.name || '',
		type: adventureToEdit?.type || 'visited',
		date: adventureToEdit?.date || null,
		link: adventureToEdit?.link || null,
		description: adventureToEdit?.description || null,
		activity_types: adventureToEdit?.activity_types || [],
		rating: adventureToEdit?.rating || NaN,
		is_public: adventureToEdit?.is_public || false,
		latitude: adventureToEdit?.latitude || NaN,
		longitude: adventureToEdit?.longitude || NaN,
		location: adventureToEdit?.location || null,
		images: adventureToEdit?.images || [],
		user_id: adventureToEdit?.user_id || null,
		collection: adventureToEdit?.collection || collection_id || null
	};

	let url: string = '';
	let imageError: string = '';
	let wikiImageError: string = '';

	images = adventure.images || [];

	if (adventure.longitude && adventure.latitude) {
		markers = [
			{
				lngLat: { lng: adventure.longitude, lat: adventure.latitude },
				location: adventure.location || '',
				name: adventure.name,
				activity_type: '',
				lng: 0
			}
		];
	}

	if (longitude && latitude) {
		adventure.latitude = latitude;
		adventure.longitude = longitude;
		reverseGeocode();
	}

	$: {
		if (!adventure.rating) {
			adventure.rating = NaN;
		}
	}

	let imageSearch: string = adventure.name || '';

	async function removeImage(id: string) {
		let res = await fetch(`/api/images/${id}/image_delete`, {
			method: 'POST'
		});
		if (res.status === 204) {
			images = images.filter((image) => image.id !== id);
			adventure.images = images;
			console.log(images);
			addToast('success', 'Image removed');
		} else {
			addToast('error', 'Failed to remove image');
		}
	}

	let isDetails: boolean = true;

	function saveAndClose() {
		dispatch('save', adventure);
		close();
	}

	$: if (markers.length > 0) {
		adventure.latitude = Math.round(markers[0].lngLat.lat * 1e6) / 1e6;
		adventure.longitude = Math.round(markers[0].lngLat.lng * 1e6) / 1e6;
		if (!adventure.location) {
			adventure.location = markers[0].location;
		}
		if (!adventure.name) {
			adventure.name = markers[0].name;
		}
	}

	async function fetchImage() {
		let res = await fetch(url);
		let data = await res.blob();
		if (!data) {
			imageError = 'No image found at that URL.';
			return;
		}
		let file = new File([data], 'image.jpg', { type: 'image/jpeg' });
		let formData = new FormData();
		formData.append('image', file);
		formData.append('adventure', adventure.id);
		let res2 = await fetch(`/adventures?/image`, {
			method: 'POST',
			body: formData
		});
		let data2 = await res2.json();
		console.log(data2);
		if (data2.type === 'success') {
			images = [...images, data2];
			adventure.images = images;
			addToast('success', 'Image uploaded');
		} else {
			addToast('error', 'Failed to upload image');
		}
	}

	async function fetchWikiImage() {
		let res = await fetch(`/api/generate/img/?name=${imageSearch}`);
		let data = await res.json();
		if (!res.ok) {
			wikiImageError = 'Failed to fetch image';
			return;
		}
		if (data.source) {
			let imageUrl = data.source;
			let res = await fetch(imageUrl);
			let blob = await res.blob();
			let file = new File([blob], `${imageSearch}.jpg`, { type: 'image/jpeg' });
			let formData = new FormData();
			formData.append('image', file);
			formData.append('adventure', adventure.id);
			let res2 = await fetch(`/adventures?/image`, {
				method: 'POST',
				body: formData
			});
			if (res2.ok) {
				let newData = deserialize(await res2.text()) as { data: { id: string; image: string } };
				console.log(newData);
				let newImage = { id: newData.data.id, image: newData.data.image };
				console.log(newImage);
				images = [...images, newImage];
				adventure.images = images;
				addToast('success', 'Image uploaded');
			} else {
				addToast('error', 'Failed to upload image');
				wikiImageError = 'Failed to upload image';
			}
		}
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
			`https://nominatim.openstreetmap.org/search?q=${adventure.latitude},${adventure.longitude}&format=jsonv2`,
			{
				headers: {
					'User-Agent': `AdventureLog / ${appVersion} `
				}
			}
		);
		let data = (await res.json()) as OpenStreetMapPlace[];
		if (data.length > 0) {
			adventure.name = data[0]?.name || '';
			adventure.activity_types?.push(data[0]?.type || '');
			adventure.location = data[0]?.display_name || '';
			if (longitude && latitude) {
				markers = [
					{
						lngLat: { lng: longitude, lat: latitude },
						location: data[0]?.display_name || '',
						name: data[0]?.name || '',
						activity_type: data[0]?.type || '',
						lng: 0
					}
				];
			}
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
		let res = await fetch(`/api/generate/desc/?name=${adventure.name}`);
		let data = await res.json();
		if (data.extract?.length > 0) {
			adventure.description = data.extract;
		} else {
			wikiError = 'No description found';
		}
	}

	function addMarker(e: CustomEvent<any>) {
		markers = [];
		markers = [
			...markers,
			{
				lngLat: e.detail.lngLat,
				name: '',
				location: '',
				activity_type: '',
				lng: 0
			}
		];
		console.log(markers);
	}

	function imageSubmit() {
		return async ({ result }: any) => {
			if (result.type === 'success') {
				if (result.data.id && result.data.image) {
					adventure.images = [...adventure.images, result.data];
					images = [...images, result.data];
					addToast('success', 'Image uploaded');

					fileInput.value = '';
					console.log(adventure);
				} else {
					addToast('error', result.data.error || 'Failed to upload image');
				}
			}
		};
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();
		console.log(adventure);
		if (adventure.id === '') {
			let res = await fetch('/api/adventures', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(adventure)
			});
			let data = await res.json();
			if (data.id) {
				adventure = data as Adventure;
				isDetails = false;
				addToast('success', 'Adventure created');
			} else {
				addToast('error', 'Failed to create adventure');
			}
		} else {
			let res = await fetch(`/api/adventures/${adventure.id}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(adventure)
			});
			let data = await res.json();
			if (data.id) {
				adventure = data as Adventure;
				isDetails = false;
				addToast('success', 'Adventure updated');
			} else {
				addToast('error', 'Failed to update adventure');
			}
		}
	}
</script>

<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
<dialog id="my_modal_1" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div class="modal-box w-11/12 max-w-2xl" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<h3 class="font-bold text-lg">Edit {adventure.type} Adventure</h3>
		{#if adventure.id === '' || isDetails}
			<div class="modal-action items-center">
				<form method="post" style="width: 100%;" on:submit={handleSubmit}>
					<!-- Grid layout for form fields -->
					<h2 class="text-2xl font-semibold mb-2">Basic Information</h2>
					<!-- <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3"> -->
					<div>
						<label for="name">Name</label><br />
						<input
							type="text"
							id="name"
							name="name"
							bind:value={adventure.name}
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
									on:click={() => (adventure.type = 'visited')}
									checked={adventure.type == 'visited'}
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
									on:click={() => (adventure.type = 'planned')}
									checked={adventure.type == 'planned'}
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
							bind:value={adventure.date}
							class="input input-bordered w-full"
						/>
					</div>
					<div>
						<!-- link -->
						<div>
							<label for="link">Link</label><br />
							<input
								type="text"
								id="link"
								name="link"
								bind:value={adventure.link}
								class="input input-bordered w-full"
							/>
						</div>
					</div>
					<div>
						<label for="description">Description</label><br />
						<textarea
							id="description"
							name="description"
							bind:value={adventure.description}
							class="textarea textarea-bordered w-full h-32"
						></textarea>
						<div class="mt-2">
							<button type="button" class="btn btn-neutral" on:click={generateDesc}
								>Generate Description</button
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
								bind:value={adventure.activity_types}
								class="input input-bordered w-full"
							/>
							<ActivityComplete bind:activities={adventure.activity_types} />
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
								bind:value={adventure.rating}
								id="rating"
								name="rating"
								class="input input-bordered w-full max-w-xs mt-1"
							/>
							<div class="rating -ml-3 mt-1">
								<input
									type="radio"
									name="rating-2"
									class="rating-hidden"
									checked={Number.isNaN(adventure.rating)}
								/>
								<input
									type="radio"
									name="rating-2"
									class="mask mask-star-2 bg-orange-400"
									on:click={() => (adventure.rating = 1)}
									checked={adventure.rating === 1}
								/>
								<input
									type="radio"
									name="rating-2"
									class="mask mask-star-2 bg-orange-400"
									on:click={() => (adventure.rating = 2)}
									checked={adventure.rating === 2}
								/>
								<input
									type="radio"
									name="rating-2"
									class="mask mask-star-2 bg-orange-400"
									on:click={() => (adventure.rating = 3)}
									checked={adventure.rating === 3}
								/>
								<input
									type="radio"
									name="rating-2"
									class="mask mask-star-2 bg-orange-400"
									on:click={() => (adventure.rating = 4)}
									checked={adventure.rating === 4}
								/>
								<input
									type="radio"
									name="rating-2"
									class="mask mask-star-2 bg-orange-400"
									on:click={() => (adventure.rating = 5)}
									checked={adventure.rating === 5}
								/>
								{#if adventure.rating}
									<button
										type="button"
										class="btn btn-sm btn-error ml-2"
										on:click={() => (adventure.rating = NaN)}
									>
										Remove
									</button>
								{/if}
							</div>
							<div>
								<div class="mt-2">
									<div>
										<label for="is_public"
											>Public <Earth class="inline-block -mt-1 mb-1 w-6 h-6" /></label
										><br />
										<input
											type="checkbox"
											class="toggle toggle-primary"
											id="is_public"
											name="is_public"
											bind:checked={adventure.is_public}
										/>
									</div>
								</div>
							</div>
						</div>
						<div class="divider"></div>
						<h2 class="text-2xl font-semibold mb-2 mt-2">Location Information</h2>
						<!-- <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3"> -->
						<div>
							<label for="latitude">Location</label><br />
							<input
								type="text"
								id="location"
								name="location"
								bind:value={adventure.location}
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
														activity_type: place.type,
														lng: 0
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
						<!-- </div> -->
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
							<button type="submit" class="btn btn-primary">Save & Next</button>
							<button type="button" class="btn" on:click={close}>Close</button>
						</div>
						{#if adventure.is_public}
							<div class="bg-neutral p-4 mt-2 rounded-md shadow-sm">
								<p class=" font-semibold">Share this Adventure!</p>
								<div class="flex items-center justify-between">
									<p class="text-card-foreground font-mono">
										{window.location.origin}/adventures/{adventure.id}
									</p>
									<button
										type="button"
										on:click={() => {
											navigator.clipboard.writeText(
												`${window.location.origin}/adventures/${adventure.id}`
											);
										}}
										class="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 h-10 px-4 py-2"
									>
										Copy Link
									</button>
								</div>
							</div>
						{/if}
					</div>
				</form>
			</div>
		{:else}
			<p>Upload images here</p>
			<!-- <p>{adventureToEdit.id}</p> -->
			<div class="mb-2">
				<label for="image">Image </label><br />
				<div class="flex">
					<form
						method="POST"
						action="/adventures?/image"
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
						<input type="hidden" name="adventure" value={adventure.id} id="adventure" />
						<button class="btn btn-neutral mt-2 mb-2" type="submit">Upload Image</button>
					</form>
				</div>
				<div class="mt-2">
					<label for="url">URL</label><br />
					<input
						type="text"
						id="url"
						name="url"
						bind:value={url}
						class="input input-bordered w-full"
					/>
					<button class="btn btn-neutral mt-2" type="button" on:click={fetchImage}
						>Fetch Image</button
					>
				</div>
				<div class="mt-2">
					<label for="name">Wikipedia</label><br />
					<input
						type="text"
						id="name"
						name="name"
						bind:value={imageSearch}
						class="input input-bordered w-full"
					/>
					<button class="btn btn-neutral mt-2" type="button" on:click={fetchWikiImage}
						>Fetch Image</button
					>
				</div>
				<div class="divider"></div>
				{#if images.length > 0}
					<h1 class="font-semibold text-xl">My Images</h1>
				{:else}
					<h1 class="font-semibold text-xl">No Images</h1>
				{/if}
				<div class="flex flex-wrap gap-2 mt-2">
					{#each images as image}
						<div class="relative h-32 w-32">
							<button
								type="button"
								class="absolute top-0 left-0 btn btn-error btn-sm z-10"
								on:click={() => removeImage(image.id)}
							>
								X
							</button>
							<img src={image.image} alt={image.id} class="w-full h-full object-cover" />
						</div>
					{/each}
				</div>
			</div>
			<div class="mt-4">
				<button type="button" class="btn btn-primary" on:click={saveAndClose}>Close</button>
			</div>
		{/if}
	</div>
</dialog>
