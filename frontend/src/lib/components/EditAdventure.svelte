<script lang="ts">
	export let adventureToEdit: Adventure;
	import { createEventDispatcher } from 'svelte';
	import type { Adventure } from '$lib/types';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	import { addToast } from '$lib/toasts';
	let modal: HTMLDialogElement;

	console.log(adventureToEdit.id);

	let originalName = adventureToEdit.name;

	let isPointModalOpen: boolean = false;

	import MapMarker from '~icons/mdi/map-marker';
	import Calendar from '~icons/mdi/calendar';
	import Notebook from '~icons/mdi/notebook';
	import ClipboardList from '~icons/mdi/clipboard-list';
	import Image from '~icons/mdi/image';
	import Star from '~icons/mdi/star';
	import Attachment from '~icons/mdi/attachment';
	import PointSelectionModal from './PointSelectionModal.svelte';

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
	function setLongLat(event: CustomEvent<[number, number]>) {
		console.log(event.detail);
		adventureToEdit.latitude = event.detail[1];
		adventureToEdit.longitude = event.detail[0];
		isPointModalOpen = false;
	}
</script>

{#if isPointModalOpen}
	<PointSelectionModal
		longitude={adventureToEdit.longitude}
		latitude={adventureToEdit.latitude}
		on:close={() => (isPointModalOpen = false)}
		on:submit={setLongLat}
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
				</div>
				<div class="mb-2">
					<label for="date">Date <Calendar class="inline-block mb-1 w-6 h-6" /></label><br />
					<input
						type="date"
						id="date"
						name="date"
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
						<!-- <button
                class="btn btn-neutral ml-2"
                type="button"
                on:click={generate}
                ><iconify-icon icon="mdi:wikipedia" class="text-xl -mb-1"
                ></iconify-icon>Generate Description</button
              > -->
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
						bind:value={adventureToEdit.activity_types}
						class="input input-bordered w-full max-w-xs mt-1"
					/>
				</div>
				<div class="mb-2">
					<label for="image">Image <Image class="inline-block -mt-1 mb-1 w-6 h-6" /></label><br />
					<input
						type="file"
						id="image"
						name="image"
						bind:value={adventureToEdit.image}
						class="file-input file-input-bordered w-full max-w-xs mt-1"
					/>
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
						name="rating"
						id="rating"
						bind:value={adventureToEdit.rating}
						class="input input-bordered w-full max-w-xs mt-1"
					/>
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
				<div class="mb-2">
					<button
						type="button"
						class="btn btn-secondary"
						on:click={() => (isPointModalOpen = true)}
					>
						{adventureToEdit.latitude && adventureToEdit.longitude ? 'Change' : 'Select'}
						Location</button
					>
				</div>

				<button type="submit" class="btn btn-primary mr-4 mt-4" on:click={submit}>Edit</button>
				<!-- if there is a button in form, it will close the modal -->
				<button class="btn mt-4" on:click={close}>Close</button>
			</form>
			<div class="flex items-center justify-center flex-wrap gap-4 mt-4"></div>
		</div>
	</div>
</dialog>