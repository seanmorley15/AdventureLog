<script lang="ts">
	export let collectionToEdit: Collection;
	import { createEventDispatcher } from 'svelte';
	import type { Collection } from '$lib/types';
	import { t } from 'svelte-i18n';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	import { addToast } from '$lib/toasts';
	let modal: HTMLDialogElement;

	console.log(collectionToEdit.id);

	let originalName = collectionToEdit.name;

	import Calendar from '~icons/mdi/calendar';
	import Notebook from '~icons/mdi/notebook';
	import Earth from '~icons/mdi/earth';

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

		if (collectionToEdit.end_date && collectionToEdit.start_date) {
			if (new Date(collectionToEdit.start_date) > new Date(collectionToEdit.end_date)) {
				addToast('error', $t('adventures.start_before_end_error'));
				return;
			}
		}
		if (collectionToEdit.end_date && !collectionToEdit.start_date) {
			addToast('error', $t('adventures.no_start_date'));
			return;
		}

		if (collectionToEdit.start_date && !collectionToEdit.end_date) {
			addToast('error', $t('adventures.no_end_date'));
			return;
		}

		const response = await fetch(form.action, {
			method: form.method,
			body: formData
		});

		if (response.ok) {
			const result = await response.json();
			const data = JSON.parse(result.data);
			console.log(data);

			if (data) {
				addToast('success', $t('collection.collection_edit_success'));
				dispatch('saveEdit', collectionToEdit);
				close();
			} else {
				addToast('warning', $t('collection.error_editing_collection'));
				console.log('Error editing collection');
			}
		}
	}
</script>

<dialog id="my_modal_1" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<div class="modal-box" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<h3 class="font-bold text-lg">{$t('adventures.edit_collection')}: {originalName}</h3>
		<div
			class="modal-action items-center"
			style="display: flex; flex-direction: column; align-items: center; width: 100%;"
		>
			<form method="post" style="width: 100%;" on:submit={handleSubmit} action="/collections?/edit">
				<div class="mb-2">
					<input
						type="text"
						id="adventureId"
						name="adventureId"
						hidden
						readonly
						bind:value={collectionToEdit.id}
						class="input input-bordered w-full max-w-xs mt-1"
					/>
					<label for="name">{$t('adventures.name')}</label><br />
					<input
						type="text"
						name="name"
						id="name"
						bind:value={collectionToEdit.name}
						class="input input-bordered w-full max-w-xs mt-1"
					/>
				</div>
				<div class="mb-2">
					<label for="date"
						>{$t('adventures.description')}
						<Notebook class="inline-block -mt-1 mb-1 w-6 h-6" /></label
					><br />
					<div class="flex">
						<input
							type="text"
							id="description"
							name="description"
							bind:value={collectionToEdit.description}
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
					<div class="mb-2">
						<label for="start_date"
							>{$t('adventures.start_date')} <Calendar class="inline-block mb-1 w-6 h-6" /></label
						><br />
						<input
							type="date"
							id="start_date"
							name="start_date"
							bind:value={collectionToEdit.start_date}
							class="input input-bordered w-full max-w-xs mt-1"
						/>
					</div>
					<div class="mb-2">
						<label for="end_date"
							>{$t('adventures.end_date')} <Calendar class="inline-block mb-1 w-6 h-6" /></label
						><br />
						<input
							type="date"
							id="end_date"
							name="end_date"
							bind:value={collectionToEdit.end_date}
							class="input input-bordered w-full max-w-xs mt-1"
						/>
					</div>
					<div class="mb-2">
						<label for="end_date">{$t('adventures.link')} </label><br />
						<input
							type="url"
							id="link"
							name="link"
							bind:value={collectionToEdit.link}
							class="input input-bordered w-full max-w-xs mt-1"
						/>
					</div>
				</div>
				<div class="mb-2">
					<label for="is_public"
						>{$t('adventures.public')} <Earth class="inline-block -mt-1 mb-1 w-6 h-6" /></label
					><br />
					<input
						type="checkbox"
						class="toggle toggle-primary"
						id="is_public"
						name="is_public"
						bind:checked={collectionToEdit.is_public}
					/>
				</div>

				{#if collectionToEdit.is_public}
					<div class="bg-neutral p-4 rounded-md shadow-sm">
						<p class=" font-semibold">{$t('adventures.share_adventure')}</p>
						<div class="flex items-center justify-between">
							<p class="text-card-foreground font-mono">
								{window.location.origin}/collections/{collectionToEdit.id}
							</p>
							<button
								type="button"
								on:click={() => {
									navigator.clipboard.writeText(
										`${window.location.origin}/collections/${collectionToEdit.id}`
									);
								}}
								class="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 h-10 px-4 py-2"
							>
								{$t('adventures.copy_link')}
							</button>
						</div>
					</div>
				{/if}

				<button type="submit" class="btn btn-primary mr-4 mt-4" on:click={submit}>Edit</button>
				<!-- if there is a button in form, it will close the modal -->
				<button class="btn mt-4" on:click={close}>{$t('about.close')}</button>
			</form>
			<div class="flex items-center justify-center flex-wrap gap-4 mt-4"></div>
		</div>
	</div>
</dialog>
