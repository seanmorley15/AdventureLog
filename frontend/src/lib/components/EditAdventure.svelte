<script lang="ts">
	export let adventureToEdit: Adventure;
	import { createEventDispatcher } from 'svelte';
	import type { Adventure } from '$lib/types';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	import { addToast } from '$lib/toasts';
	let modal: HTMLDialogElement;

	export let startDate: string | null = null;
	export let endDate: string | null = null;

	console.log(adventureToEdit.id);

	let originalName = adventureToEdit.name;

	let isPointModalOpen: boolean = false;
	let isImageFetcherOpen: boolean = false;

	let fileInput: HTMLInputElement;
	let image: File;

	import MapMarker from '~icons/mdi/map-marker';
	import Map from '~icons/mdi/map';
	import Calendar from '~icons/mdi/calendar';
	import Notebook from '~icons/mdi/notebook';
	import ClipboardList from '~icons/mdi/clipboard-list';
	import Star from '~icons/mdi/star';
	import Attachment from '~icons/mdi/attachment';
	import PointSelectionModal from './PointSelectionModal.svelte';
	import Earth from '~icons/mdi/earth';
	import Wikipedia from '~icons/mdi/wikipedia';
	import ImageFetcher from './ImageFetcher.svelte';
	import ActivityComplete from './ActivityComplete.svelte';

	onMount(async () => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}
	});

	function submit() {}

	function close() {
		dispatch('close');
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			close();
		}
	}

	async function generateDesc() {
		let res = await fetch(`/api/generate/desc/?name=${adventureToEdit.name}`);
		let data = await res.json();
		if (data.extract) {
			adventureToEdit.description = data.extract;
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
			const data = JSON.parse(result.data);
			console.log(data);

			if (data) {
				if (typeof adventureToEdit.activity_types === 'string') {
					adventureToEdit.activity_types = (adventureToEdit.activity_types as string)
						.split(',')
						.map((activity_type) => activity_type.trim())
						.filter((activity_type) => activity_type !== '' && activity_type !== ',');

					// Remove duplicates
					adventureToEdit.activity_types = Array.from(new Set(adventureToEdit.activity_types));
				}

				adventureToEdit.image = data[1];
				adventureToEdit.link = data[2];
				addToast('success', 'Adventure edited successfully!');
				dispatch('saveEdit', adventureToEdit);
				close();
			} else {
				addToast('warning', 'Error editing adventure');
				console.log('Error editing adventure');
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
			adventureToEdit.image = file;
		}
		isImageFetcherOpen = false;
	}

	function setLongLat(event: CustomEvent<Adventure>) {
		console.log(event.detail);
		isPointModalOpen = false;
	}
</script>

{#if isPointModalOpen}
	<PointSelectionModal
		bind:adventure={adventureToEdit}
		on:close={() => (isPointModalOpen = false)}
		on:submit={setLongLat}
		query={adventureToEdit.name}
	/>
{/if}

{#if isImageFetcherOpen}
	<ImageFetcher
		on:image={handleImageFetch}
		name={adventureToEdit.name}
		on:close={() => (isImageFetcherOpen = false)}
	/>
{/if}

<dialog id="my_modal_1" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<div class="modal-box" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<h3 class="font-bold text-lg">Edit Adventure: {originalName}</h3>
		<div
			class="modal-action items-center"
			style="display: flex; flex-direction: column; align-items: center; width: 100%;"
		>
			<form method="post" style="width: 100%;" on:submit={handleSubmit} action="/adventures?/edit">
				<div class="mb-2">
					<input
						type="text"
						id="adventureId"
						name="adventureId"
						hidden
						readonly
						bind:value={adventureToEdit.id}
						class="input input-bordered w-full max-w-xs mt-1"
					/>
					<input
						type="text"
						id="type"
						name="type"
						hidden
						readonly
						bind:value={adventureToEdit.type}
						class="input input-bordered w-full max-w-xs mt-1"
					/>
					<label for="name">Name</label><br />
					<input
						type="text"
						name="name"
						id="name"
						bind:value={adventureToEdit.name}
						class="input input-bordered w-full max-w-xs mt-1"
					/>
				</div>
				<div class="mb-2">
					<label for="location">Location<MapMarker class="inline-block -mt-1 mb-1 w-6 h-6" /></label
					><br />
					<input
						type="text"
						id="location"
						name="location"
						bind:value={adventureToEdit.location}
						class="input input-bordered w-full max-w-xs mt-1"
					/>
					<div class="mb-2 mt-2">
						<button
							type="button"
							class="btn btn-secondary"
							on:click={() => (isPointModalOpen = true)}
						>
							<Map class="inline-block w-6 h-6" />{adventureToEdit.latitude &&
							adventureToEdit.longitude
								? 'Change'
								: 'Select'}
							Location</button
						>
					</div>
				</div>
				<div class="mb-2">
					<label for="date">Date <Calendar class="inline-block mb-1 w-6 h-6" /></label><br />
					<input
						type="date"
						id="date"
						name="date"
						min={startDate || ''}
						max={endDate || ''}
						bind:value={adventureToEdit.date}
						class="input input-bordered w-full max-w-xs mt-1"
					/>
				</div>
				<div class="mb-2">
					<label for="date">Description <Notebook class="inline-block -mt-1 mb-1 w-6 h-6" /></label
					><br />
					<div class="flex">
						<input
							type="text"
							id="description"
							name="description"
							bind:value={adventureToEdit.description}
							class="input input-bordered w-full max-w-xs mt-1 mb-2"
						/>
						<button class="btn btn-neutral ml-2" type="button" on:click={generateDesc}
							><Wikipedia class="inline-block -mt-1 mb-1 w-6 h-6" />Generate Description</button
						>
					</div>
				</div>
				{#if adventureToEdit.type == 'visited' || adventureToEdit.type == 'planned'}
					<div class="mb-2">
						<label for="activityTypes"
							>Activity Types <ClipboardList class="inline-block -mt-1 mb-1 w-6 h-6" /></label
						><br />
						<input
							type="text"
							id="activity_types"
							name="activity_types"
							hidden
							bind:value={adventureToEdit.activity_types}
							class="input input-bordered w-full max-w-xs mt-1"
						/>
						<ActivityComplete bind:activities={adventureToEdit.activity_types} />
					</div>
				{/if}
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
					<label for="link">Link <Attachment class="inline-block -mt-1 mb-1 w-6 h-6" /></label><br
					/>
					<input
						type="url"
						id="link"
						name="link"
						bind:value={adventureToEdit.link}
						class="input input-bordered w-full max-w-xs mt-1"
					/>
				</div>
				<div class="mb-2">
					<label for="rating">Rating <Star class="inline-block -mt-1 mb-1 w-6 h-6" /></label><br />
					<input
						type="number"
						min="0"
						max="5"
						hidden
						bind:value={adventureToEdit.rating}
						id="rating"
						name="rating"
						class="input input-bordered w-full max-w-xs mt-1"
					/>
					<div class="rating -ml-3 mt-1 mb-4">
						<input
							type="radio"
							name="rating-2"
							class="rating-hidden"
							checked={Number.isNaN(adventureToEdit.rating) || adventureToEdit.rating === null}
						/>
						<input
							type="radio"
							name="rating-2"
							class="mask mask-star-2 bg-orange-400"
							checked={adventureToEdit.rating === 1}
							on:click={() => (adventureToEdit.rating = 1)}
						/>
						<input
							type="radio"
							name="rating-2"
							class="mask mask-star-2 bg-orange-400"
							on:click={() => (adventureToEdit.rating = 2)}
							checked={adventureToEdit.rating === 2}
						/>
						<input
							type="radio"
							name="rating-2"
							class="mask mask-star-2 bg-orange-400"
							on:click={() => (adventureToEdit.rating = 3)}
							checked={adventureToEdit.rating === 3}
						/>
						<input
							type="radio"
							name="rating-2"
							class="mask mask-star-2 bg-orange-400"
							on:click={() => (adventureToEdit.rating = 4)}
							checked={adventureToEdit.rating === 4}
						/>
						<input
							type="radio"
							name="rating-2"
							class="mask mask-star-2 bg-orange-400"
							on:click={() => (adventureToEdit.rating = 5)}
							checked={adventureToEdit.rating === 5}
						/>
						{#if adventureToEdit.rating}
							<button
								type="button"
								class="btn btn-sm btn-error ml-2"
								on:click={() => (adventureToEdit.rating = NaN)}
							>
								Remove
							</button>
						{/if}
					</div>
					<input
						type="text"
						id="latitude"
						hidden
						name="latitude"
						bind:value={adventureToEdit.latitude}
						class="input input-bordered w-full max-w-xs mt-1"
					/>
					<input
						type="text"
						id="longitude"
						hidden
						name="longitude"
						bind:value={adventureToEdit.longitude}
						class="input input-bordered w-full max-w-xs mt-1"
					/>
					{#if adventureToEdit.collection === null}
						<div class="mb-2">
							<label for="is_public">Public <Earth class="inline-block -mt-1 mb-1 w-6 h-6" /></label
							><br />
							<input
								type="checkbox"
								class="toggle toggle-primary"
								id="is_public"
								name="is_public"
								bind:checked={adventureToEdit.is_public}
							/>
						</div>
					{/if}

					{#if adventureToEdit.is_public}
						<div class="bg-neutral p-4 rounded-md shadow-sm">
							<p class=" font-semibold">Share this Adventure!</p>
							<div class="flex items-center justify-between">
								<p class="text-card-foreground font-mono">
									{window.location.origin}/adventures/{adventureToEdit.id}
								</p>
								<button
									type="button"
									on:click={() => {
										navigator.clipboard.writeText(
											`${window.location.origin}/adventures/${adventureToEdit.id}`
										);
									}}
									class="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 h-10 px-4 py-2"
								>
									Copy Link
								</button>
							</div>
						</div>
					{/if}

					<button
						type="submit"
						id="edit_adventure"
						data-umami-event="Edit Adventure"
						class="btn btn-primary mr-4 mt-4"
						on:click={submit}>Edit</button
					>
					<!-- if there is a button in form, it will close the modal -->
					<button class="btn mt-4" on:click={close}>Close</button>
				</div>
			</form>
			<div class="flex items-center justify-center flex-wrap gap-4 mt-4"></div>
		</div>
	</div>
</dialog>
