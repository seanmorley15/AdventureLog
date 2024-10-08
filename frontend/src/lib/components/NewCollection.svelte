<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { Adventure, Collection } from '$lib/types';
	import { onMount } from 'svelte';
	import { enhance } from '$app/forms';
	import { addToast } from '$lib/toasts';

	import Calendar from '~icons/mdi/calendar';

	let newCollection: Collection = {
		user_id: NaN,
		id: '',
		name: '',
		description: '',
		adventures: [] as Adventure[],
		is_public: false,
		shared_with: [],
		link: ''
	};

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

	async function handleSubmit(event: Event) {
		event.preventDefault();
		const form = event.target as HTMLFormElement;
		const formData = new FormData(form);

		// make sure that start_date is before end_date
		if (new Date(newCollection.start_date ?? '') > new Date(newCollection.end_date ?? '')) {
			addToast('error', 'Start date must be before end date');
			return;
		}

		// make sure end date has a start date
		if (newCollection.end_date && !newCollection.start_date) {
			addToast('error', 'Please provide a start date');
			return;
		}

		if (newCollection.start_date && !newCollection.end_date) {
			addToast('error', 'Please provide an end date');
			return;
		}

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

				if (id !== undefined && user_id !== undefined) {
					newCollection.id = id;
					newCollection.user_id = user_id;
					console.log(newCollection);
					dispatch('create', newCollection);
					addToast('success', 'Collection created successfully!');
					close();
				} else {
					addToast('error', 'Error creating collection');
				}
			}
		}
	}
</script>

<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
<dialog id="my_modal_1" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div class="modal-box" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<h3 class="font-bold text-lg">New Collection</h3>
		<div
			class="modal-action items-center"
			style="display: flex; flex-direction: column; align-items: center; width: 100%;"
		>
			<form
				method="post"
				style="width: 100%;"
				on:submit={handleSubmit}
				action="/collections?/create"
			>
				<div class="mb-2">
					<label for="name">Name</label><br />
					<input
						type="text"
						id="name"
						name="name"
						bind:value={newCollection.name}
						class="input input-bordered w-full max-w-xs mt-1"
						required
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
							bind:value={newCollection.description}
							class="input input-bordered w-full max-w-xs mt-1 mb-2"
						/>
					</div>
					<div class="mb-2">
						<label for="start_date">Start Date <Calendar class="inline-block mb-1 w-6 h-6" /></label
						><br />
						<input
							type="date"
							id="start_date"
							name="start_date"
							bind:value={newCollection.start_date}
							class="input input-bordered w-full max-w-xs mt-1"
						/>
					</div>
					<div class="mb-2">
						<label for="end_date">End Date <Calendar class="inline-block mb-1 w-6 h-6" /></label><br
						/>
						<input
							type="date"
							id="end_date"
							name="end_date"
							bind:value={newCollection.end_date}
							class="input input-bordered w-full max-w-xs mt-1"
						/>
					</div>
					<div class="mb-2">
						<label for="end_date">Link </label><br />
						<input
							type="url"
							id="link"
							name="link"
							bind:value={newCollection.link}
							class="input input-bordered w-full max-w-xs mt-1"
						/>
					</div>
					<div class="mb-2">
						<button type="submit" class="btn btn-primary mr-4 mt-4">Create</button>
						<button type="button" class="btn mt-4" on:click={close}>Close</button>
					</div>
				</div>
			</form>
		</div>
	</div>
</dialog>
