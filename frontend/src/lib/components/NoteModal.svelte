<script lang="ts">
	import { isValidUrl } from '$lib';
	import type { Collection, Note, User } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import MarkdownEditor from './MarkdownEditor.svelte';
	let modal: HTMLDialogElement;
	import { marked } from 'marked'; // Import the markdown parser

	const renderMarkdown = (markdown: string) => {
		return marked(markdown);
	};

	export let note: Note | null = null;
	export let collection: Collection;
	export let user: User | null = null;

	let constrainDates: boolean = true;

	let isReadOnly =
		!(note && user?.uuid == note?.user) &&
		!(user && collection && collection.shared_with && collection.shared_with.includes(user.uuid)) &&
		!!note;

	let warning: string | null = '';

	let newLink: string = '';

	function addLink() {
		// check to make it a valid URL
		if (!isValidUrl(newLink)) {
			warning = $t('notes.invalid_url');
			return;
		} else {
			warning = null;
		}

		if (newLink.trim().length > 0) {
			newNote.links = [...newNote.links, newLink];
			newLink = '';
		}
		console.log(newNote.links);
	}

	let newNote = {
		name: note?.name || '',
		content: note?.content || '',
		date: note?.date || undefined || null,
		links: note?.links || [],
		collection: collection.id,
		is_public: collection.is_public
	};

	let initialName: string = note?.name || '';

	onMount(() => {
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
			dispatch('close');
		}
	}

	async function save() {
		// handles empty date
		if (newNote.date == '') {
			newNote.date = null;
		}

		if (note && note.id) {
			console.log('newNote', newNote);
			const res = await fetch(`/api/notes/${note.id}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(newNote)
			});
			if (res.ok) {
				let data = await res.json();
				if (data) {
					dispatch('save', data);
				}
			} else {
				console.error('Failed to save note');
			}
		} else {
			console.log('newNote', newNote);
			const res = await fetch(`/api/notes/`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(newNote)
			});
			if (res.ok) {
				let data = await res.json();
				if (data) {
					dispatch('create', data);
				}
			} else {
				let data = await res.json();
				console.error($t('notes.failed_to_save'), data);
			}
		}
	}
</script>

<dialog id="my_modal_1" class="modal backdrop-blur-sm">
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div
		class="modal-box w-11/12 max-w-6xl bg-gradient-to-br from-base-100 via-base-100 to-base-200 border border-base-300 shadow-2xl"
		role="dialog"
		on:keydown={handleKeydown}
		tabindex="0"
	>
		<!-- Header Section -->
		<div
			class="top-0 z-10 bg-base-100/90 backdrop-blur-lg border-b border-base-300 -mx-6 -mt-6 px-6 py-4 mb-6"
		>
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-3">
					<div class="p-2 bg-primary/10 rounded-xl">
						{#if isReadOnly}
							<svg
								class="w-8 h-8 text-primary"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
								/>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
								/>
							</svg>
						{:else}
							<svg
								class="w-8 h-8 text-primary"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
								/>
							</svg>
						{/if}
					</div>
					<div>
						<h1 class="text-3xl font-bold text-primary bg-clip-text">
							{#if note?.id && !isReadOnly}
								{$t('notes.editing_note')}
							{:else if !isReadOnly}
								{$t('notes.note_editor')}
							{:else}
								{$t('notes.note_viewer')}
							{/if}
						</h1>
						<p class="text-sm text-base-content/60">
							{#if note?.id && !isReadOnly}
								{$t('notes.update_note_details')} "{initialName}"
							{:else if !isReadOnly}
								{$t('notes.create_new_note')}
							{:else}
								{$t('notes.viewing_note')} "{note?.name || ''}"
							{/if}
						</p>
					</div>
				</div>

				<!-- Close Button -->
				<button class="btn btn-ghost btn-square" on:click={close}>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						/>
					</svg>
				</button>
			</div>
		</div>

		<!-- Main Content -->
		<div class="px-2">
			<form method="post" style="width: 100%;" on:submit|preventDefault>
				<!-- Basic Information Section -->
				<div
					class="collapse collapse-plus bg-base-200/50 border border-base-300/50 mb-6 rounded-2xl overflow-hidden"
				>
					<input type="checkbox" checked />
					<div
						class="collapse-title text-xl font-semibold bg-gradient-to-r from-primary/10 to-primary/5"
					>
						<div class="flex items-center gap-3">
							<div class="p-2 bg-primary/10 rounded-lg">
								<svg
									class="w-5 h-5 text-primary"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
									/>
								</svg>
							</div>
							{$t('adventures.basic_information')}
						</div>
					</div>
					<div class="collapse-content bg-base-100/50 pt-4 p-6 space-y-3">
						<!-- Dual Column Layout for Large Screens -->
						<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
							<!-- Left Column -->
							<div class="space-y-4">
								<!-- Name Field -->
								<div class="form-control">
									<label class="label" for="name">
										<span class="label-text font-medium"
											>{$t('adventures.name')}<span class="text-error ml-1">*</span></span
										>
									</label>
									<input
										type="text"
										id="name"
										name="name"
										readonly={isReadOnly}
										bind:value={newNote.name}
										class="input input-bordered w-full bg-base-100/80 focus:bg-base-100"
										placeholder={$t('notes.enter_note_title')}
										required
									/>
								</div>

								<!-- Date Field -->
								<div class="form-control">
									<label class="label" for="date">
										<span class="label-text font-medium">{$t('adventures.date')}</span>
									</label>
									{#if collection && collection.start_date && collection.end_date && !isReadOnly}
										<div class="flex items-center gap-2 mb-2">
											<input
												type="checkbox"
												class="toggle toggle-primary toggle-sm"
												id="constrain_dates"
												name="constrain_dates"
												bind:checked={constrainDates}
											/>
											<span class="text-sm text-base-content/70"
												>{$t('adventures.date_constrain')}</span
											>
										</div>
									{/if}
									<input
										type="date"
										id="date"
										name="date"
										readonly={isReadOnly}
										min={constrainDates ? collection.start_date : ''}
										max={constrainDates ? collection.end_date : ''}
										bind:value={newNote.date}
										class="input input-bordered w-full bg-base-100/80 focus:bg-base-100"
									/>
								</div>
							</div>

							<!-- Right Column - Links Section -->
							<div class="space-y-4">
								{#if !isReadOnly}
									<div class="form-control">
										<label class="label" for="new-link">
											<span class="label-text font-medium">{$t('adventures.links')}</span>
										</label>
										<div class="join w-full">
											<input
												type="url"
												id="new-link"
												class="input input-bordered join-item flex-1 bg-base-100/80 focus:bg-base-100"
												placeholder="https://example.com"
												bind:value={newLink}
												on:keydown={(e) => {
													if (e.key === 'Enter') {
														e.preventDefault();
														addLink();
													}
												}}
											/>
											<button type="button" class="btn btn-primary join-item" on:click={addLink}>
												<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														stroke-width="2"
														d="M12 6v6m0 0v6m0-6h6m-6 0H6"
													/>
												</svg>
											</button>
										</div>
									</div>
								{/if}

								<!-- Links List -->
								{#if newNote.links.length > 0}
									<div class="max-h-48 overflow-y-auto space-y-2">
										{#each newNote.links as link, i}
											<div
												class="flex items-center gap-2 p-3 bg-base-200/50 rounded-xl border border-base-300/50"
											>
												<svg
													class="w-4 h-4 text-primary flex-shrink-0"
													fill="none"
													stroke="currentColor"
													viewBox="0 0 24 24"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														stroke-width="2"
														d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
													/>
												</svg>
												<a
													href={link}
													class="link link-primary text-sm truncate flex-1"
													target="_blank"
													rel="noopener noreferrer"
												>
													{link}
												</a>
												{#if !isReadOnly}
													<button
														type="button"
														class="btn btn-ghost btn-xs text-error"
														on:click={() => {
															newNote.links = newNote.links.filter((_, index) => index !== i);
														}}
													>
														<svg
															class="w-4 h-4"
															fill="none"
															stroke="currentColor"
															viewBox="0 0 24 24"
														>
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																stroke-width="2"
																d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
															/>
														</svg>
													</button>
												{/if}
											</div>
										{/each}
									</div>
								{/if}
							</div>
						</div>
					</div>
				</div>

				<!-- Content Section -->
				<div
					class="collapse collapse-plus bg-base-200/50 border border-base-300/50 mb-6 rounded-2xl overflow-hidden"
				>
					<input type="checkbox" checked />
					<div
						class="collapse-title text-xl font-semibold bg-gradient-to-r from-primary/10 to-primary/5"
					>
						<div class="flex items-center gap-3">
							<div class="p-2 bg-primary/10 rounded-lg">
								<svg
									class="w-5 h-5 text-primary"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
									/>
								</svg>
							</div>
							{$t('notes.content')}
						</div>
					</div>
					<div class="collapse-content bg-base-100/50 pt-4 p-6">
						{#if !isReadOnly}
							<MarkdownEditor bind:text={newNote.content} editor_height={'h-96'} />
						{:else if note}
							<div
								class="bg-base-100 border border-base-300/50 rounded-xl p-6 max-h-96 overflow-y-auto"
							>
								<article class="prose max-w-full">
									{@html renderMarkdown(note.content || '')}
								</article>
							</div>
						{/if}
					</div>
				</div>

				<!-- Warning Messages -->
				{#if warning}
					<div role="alert" class="alert alert-error mb-6 rounded-xl border border-error/20">
						<svg class="h-6 w-6 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
							/>
						</svg>
						<span class="font-medium">{warning}</span>
					</div>
				{/if}

				<!-- Public Note Alert -->
				{#if collection.is_public}
					<div role="alert" class="alert alert-info mb-6 rounded-xl border border-info/20">
						<svg class="h-6 w-6 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
							/>
						</svg>
						<span class="font-medium">{$t('notes.note_public')}</span>
					</div>
				{/if}

				<!-- Action Buttons -->
				<div class="flex gap-3 justify-end pt-4 border-t border-base-300/50">
					<button type="button" class="btn btn-neutral-200" on:click={close}>
						<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M6 18L18 6M6 6l12 12"
							/>
						</svg>
						{$t('about.close')}
					</button>
					{#if !isReadOnly}
						<button type="button" class="btn btn-primary" on:click={save}>
							<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"
								/>
							</svg>
							{$t('notes.save')}
						</button>
					{/if}
				</div>
			</form>
		</div>
	</div>
</dialog>
