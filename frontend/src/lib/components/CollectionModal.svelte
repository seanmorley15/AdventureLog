<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { Collection, Transportation } from '$lib/types';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	import { addToast } from '$lib/toasts';
	let modal: HTMLDialogElement;
	import { t } from 'svelte-i18n';

	import MarkdownEditor from './MarkdownEditor.svelte';

	export let collectionToEdit: Collection | null = null;

	let collection: Collection = {
		id: collectionToEdit?.id || '',
		name: collectionToEdit?.name || '',
		description: collectionToEdit?.description || '',
		start_date: collectionToEdit?.start_date || null,
		end_date: collectionToEdit?.end_date || null,
		user: collectionToEdit?.user || '',
		is_public: collectionToEdit?.is_public || false,
		adventures: collectionToEdit?.adventures || [],
		link: collectionToEdit?.link || '',
		shared_with: undefined
	};

	console.log(collection);

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
		console.log(collection);

		if (collection.start_date && !collection.end_date) {
			collection.end_date = collection.start_date;
		}

		if (
			collection.start_date &&
			collection.end_date &&
			collection.start_date > collection.end_date
		) {
			addToast('error', $t('adventures.start_before_end_error'));
			return;
		}

		if (!collection.start_date && collection.end_date) {
			collection.start_date = collection.end_date;
		}

		if (!collection.start_date && !collection.end_date) {
			collection.start_date = null;
			collection.end_date = null;
		}

		if (collection.id === '') {
			let res = await fetch('/api/collections', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(collection)
			});
			let data = await res.json();
			if (data.id) {
				collection = data as Collection;
				addToast('success', $t('collection.collection_created'));
				dispatch('save', collection);
			} else {
				console.error(data);
				addToast('error', $t('collection.error_creating_collection'));
			}
		} else {
			let res = await fetch(`/api/collections/${collection.id}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(collection)
			});
			let data = await res.json();
			if (data.id) {
				collection = data as Collection;
				addToast('success', $t('collection.collection_edit_success'));
				dispatch('save', collection);
			} else {
				addToast('error', $t('collection.error_editing_collection'));
			}
		}
	}
</script>

<dialog id="my_modal_1" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div class="modal-box w-11/12 max-w-3xl" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<h3 class="font-bold text-2xl">
			{collectionToEdit ? $t('adventures.edit_collection') : $t('collection.new_collection')}
		</h3>
		<div class="modal-action items-center">
			<form method="post" style="width: 100%;" on:submit={handleSubmit}>
				<!-- Basic Information Section -->
				<div class="collapse collapse-plus bg-base-200 mb-4">
					<input type="checkbox" checked />
					<div class="collapse-title text-xl font-medium">
						{$t('adventures.basic_information')}
					</div>
					<div class="collapse-content">
						<!-- Name -->
						<div>
							<label for="name">
								{$t('adventures.name')}<span class="text-red-500">*</span>
							</label>
							<input
								type="text"
								id="name"
								name="name"
								bind:value={collection.name}
								class="input input-bordered w-full"
								required
							/>
						</div>
						<!-- Description -->
						<div>
							<label for="description">{$t('adventures.description')}</label><br />
							<MarkdownEditor bind:text={collection.description} editor_height={'h-32'} />
						</div>
						<!-- Start Date -->
						<div>
							<label for="start_date">{$t('adventures.start_date')}</label>
							<input
								type="date"
								id="start_date"
								name="start_date"
								bind:value={collection.start_date}
								class="input input-bordered w-full"
							/>
						</div>
						<!-- End Date -->
						<div>
							<label for="end_date">{$t('adventures.end_date')}</label>
							<input
								type="date"
								id="end_date"
								name="end_date"
								bind:value={collection.end_date}
								class="input input-bordered w-full"
							/>
						</div>
						<!-- Public -->
						<div>
							<label class="label cursor-pointer flex items-start space-x-2">
								<span class="label-text">{$t('collection.public_collection')}</span>
								<input
									type="checkbox"
									class="toggle toggle-primary"
									id="is_public"
									name="is_public"
									bind:checked={collection.is_public}
								/>
							</label>
						</div>
						<!-- Link -->
						<div>
							<label for="link">{$t('adventures.link')}</label>
							<input
								type="text"
								id="link"
								name="link"
								bind:value={collection.link}
								class="input input-bordered w-full"
							/>
						</div>
					</div>
				</div>

				{#if !collection.start_date && !collection.end_date}
					<div class="mt-4">
						<div role="alert" class="alert alert-neutral">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								class="h-6 w-6 shrink-0 stroke-current"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
								></path>
							</svg>
							<span>{$t('adventures.collection_no_start_end_date')}</span>
						</div>
					</div>
				{/if}

				<div class="mt-4">
					<button type="submit" class="btn btn-primary">
						{$t('notes.save')}
					</button>
					<button type="button" class="btn" on:click={close}>
						{$t('about.close')}
					</button>
				</div>

				{#if collection.is_public && collection.id}
					<div class="bg-neutral p-4 mt-2 rounded-md shadow-sm text-neutral-content">
						<p class=" font-semibold">{$t('adventures.share_collection')}</p>
						<div class="flex items-center justify-between">
							<p class="text-card-foreground font-mono">
								{window.location.origin}/collections/{collection.id}
							</p>
							<button
								type="button"
								on:click={() => {
									navigator.clipboard.writeText(
										`${window.location.origin}/collections/${collection.id}`
									);
								}}
								class="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 h-10 px-4 py-2"
							>
								{$t('adventures.copy_link')}
							</button>
						</div>
					</div>
				{/if}
			</form>
		</div>
	</div>
</dialog>
