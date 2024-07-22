<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { Adventure, Point } from '$lib/types';
	import { onMount } from 'svelte';
	import { enhance } from '$app/forms';
	import { addToast } from '$lib/toasts';
	import PointSelectionModal from './PointSelectionModal.svelte';
	import ImageFetcher from './ImageFetcher.svelte';

	export let type: string = 'visited';

	import Wikipedia from '~icons/mdi/wikipedia';
	import ClipboardList from '~icons/mdi/clipboard-list';
	import ActivityComplete from './ActivityComplete.svelte';

	let newAdventure: Adventure = {
		id: NaN,
		type: type,
		name: '',
		location: '',
		date: '',
		description: '',
		activity_types: [],
		rating: NaN,
		link: '',
		image: '',
		user_id: NaN,
		latitude: null,
		longitude: null,
		is_public: false,
		collection: null
	};

	let image: File;
	let fileInput: HTMLInputElement;

	let isPointModalOpen: boolean = false;
	let isImageFetcherOpen: boolean = false;

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
		if (data.extract) {
			newAdventure.description = data.extract;
		}
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();
		const form = event.target as HTMLFormElement;
		const formData = new FormData(form);

		const response = await fetch(form.action, {
			method: form.method,
			body: formData
		});

		if (response.ok) {
			const result = await response.json();
			const data = JSON.parse(result.data); // Parsing the JSON string in the data field

			if (data[1] !== undefined) {
				// these two lines here are wierd, because the data[1] is the id of the new adventure and data[2] is the user_id of the new adventure
				console.log(data);
				let id = data[1];
				let user_id = data[2];
				let image_url = data[3];
				let link = data[4];
				newAdventure.image = image_url;
				newAdventure.id = id;
				newAdventure.user_id = user_id;
				newAdventure.link = link;
				// turn the activity_types string into an array by splitting it at the commas
				if (typeof newAdventure.activity_types === 'string') {
					newAdventure.activity_types = (newAdventure.activity_types as string)
						.split(',')
						.map((activity_type) => activity_type.trim())
						.filter((activity_type) => activity_type !== '' && activity_type !== ',');

					// Remove duplicates
					newAdventure.activity_types = Array.from(new Set(newAdventure.activity_types));
				}
				console.log(newAdventure);
				dispatch('create', newAdventure);
				addToast('success', 'Adventure created successfully!');
				close();
			}
		}
	}

	function handleImageFetch(event: CustomEvent) {
		const file = event.detail.file;
		if (file && fileInput) {
			// Create a DataTransfer object and add the file
			const dataTransfer = new DataTransfer();
			dataTransfer.items.add(file);

			// Set the files property of the file input
			fileInput.files = dataTransfer.files;

			// Update the adventureToEdit object
			newAdventure.image = file;
		}
		isImageFetcherOpen = false;
	}

	function setLongLat(event: CustomEvent<[number, number]>) {
		console.log(event.detail);
		newAdventure.latitude = event.detail[1];
		newAdventure.longitude = event.detail[0];
		isPointModalOpen = false;
	}
</script>

{#if isPointModalOpen}
	<PointSelectionModal
		query={newAdventure.name}
		on:close={() => (isPointModalOpen = false)}
		on:submit={setLongLat}
	/>
{/if}

{#if isImageFetcherOpen}
	<ImageFetcher
		on:image={handleImageFetch}
		name={newAdventure.name}
		on:close={() => (isImageFetcherOpen = false)}
	/>
{/if}

<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
<dialog id="my_modal_1" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div class="modal-box" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<h3 class="font-bold text-lg">New {type} Adventure</h3>
		<div
			class="modal-action items-center"
			style="display: flex; flex-direction: column; align-items: center; width: 100%;"
		>
			<form
				method="post"
				style="width: 100%;"
				on:submit={handleSubmit}
				action="/adventures?/create"
			>
				<input
					type="text"
					name="type"
					id="type"
					value={type}
					hidden
					readonly
					class="input input-bordered w-full max-w-xs mt-1"
				/>
				<div class="mb-2">
					<label for="name">Name</label><br />
					<input
						type="text"
						id="name"
						name="name"
						bind:value={newAdventure.name}
						class="input input-bordered w-full max-w-xs mt-1"
						required
					/>
				</div>
				<div class="mb-2">
					<label for="location"
						>Location<iconify-icon icon="mdi:map-marker" class="text-lg ml-0.5 -mb-0.5"
						></iconify-icon></label
					><br />
					<input
						type="text"
						id="location"
						name="location"
						bind:value={newAdventure.location}
						class="input input-bordered w-full max-w-xs mt-1"
					/>
				</div>
				<div class="mb-2">
					<label for="date"
						>Date<iconify-icon icon="mdi:calendar" class="text-lg ml-1 -mb-0.5"
						></iconify-icon></label
					><br />
					<input
						type="date"
						id="date"
						name="date"
						bind:value={newAdventure.date}
						class="input input-bordered w-full max-w-xs mt-1"
					/>
				</div>
				<div class="mb-2">
					<label for="description"
						>Description<iconify-icon icon="mdi:notebook" class="text-lg ml-1 -mb-0.5"
						></iconify-icon></label
					><br />
					<div class="flex">
						<input
							type="text"
							id="description"
							name="description"
							bind:value={newAdventure.description}
							class="input input-bordered w-full max-w-xs mt-1 mb-2"
						/>
						<button class="btn btn-neutral ml-2" type="button" on:click={generateDesc}
							><Wikipedia class="inline-block -mt-1 mb-1 w-6 h-6" />Generate Description</button
						>
					</div>
				</div>
				<div class="mb-2">
					<label for="activityTypes"
						>Activity Types <ClipboardList class="inline-block -mt-1 mb-1 w-6 h-6" /></label
					><br />
					<input
						type="text"
						id="activity_types"
						name="activity_types"
						hidden
						bind:value={newAdventure.activity_types}
						class="input input-bordered w-full max-w-xs mt-1"
					/>
					<ActivityComplete bind:activities={newAdventure.activity_types} />
				</div>
				<div class="mb-2">
					<label for="rating"
						>Rating <iconify-icon icon="mdi:star" class="text-xl -mb-1"></iconify-icon></label
					><br />
					<input
						type="number"
						min="0"
						max="5"
						bind:value={newAdventure.rating}
						id="rating"
						name="rating"
						class="input input-bordered w-full max-w-xs mt-1"
					/>
				</div>
				<div class="mb-2">
					<label for="link"
						>Link <iconify-icon icon="mdi:link" class="text-xl -mb-1"></iconify-icon></label
					><br />
					<input
						type="text"
						id="link"
						name="link"
						bind:value={newAdventure.link}
						class="input input-bordered w-full max-w-xs mt-1"
					/>
				</div>
				<div class="mb-2">
					<label for="image">Image </label><br />
					<div class="flex">
						<input
							type="file"
							id="image"
							name="image"
							bind:value={image}
							bind:this={fileInput}
							class="file-input file-input-bordered w-full max-w-xs mt-1"
						/>
						<button
							class="btn btn-neutral ml-2"
							type="button"
							on:click={() => (isImageFetcherOpen = true)}
							><Wikipedia class="inline-block -mt-1 mb-1 w-6 h-6" />Image Search</button
						>
					</div>
				</div>
				<div class="mb-2">
					<input
						type="text"
						id="latitude"
						hidden
						name="latitude"
						bind:value={newAdventure.latitude}
						class="input input-bordered w-full max-w-xs mt-1"
					/>
				</div>
				<div class="mb-2">
					<input
						type="text"
						id="longitude"
						name="longitude"
						hidden
						bind:value={newAdventure.longitude}
						class="input input-bordered w-full max-w-xs mt-1"
					/>
					<div class="mb-2">
						<button
							type="button"
							class="btn btn-secondary"
							on:click={() => (isPointModalOpen = true)}>Define Location</button
						>
					</div>
					<button type="submit" class="btn btn-primary mr-4 mt-4">Create</button>
					<button type="button" class="btn mt-4" on:click={close}>Close</button>
				</div>
			</form>
		</div>
	</div>
</dialog>
