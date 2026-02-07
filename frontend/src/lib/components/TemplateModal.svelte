<script lang="ts">
	import type { Collection, SlimCollection } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	import { addToast } from '$lib/toasts';
	let modal: HTMLDialogElement;
	import { t } from 'svelte-i18n';

	import FileDocumentPlus from '~icons/mdi/file-document-plus';
	import Clear from '~icons/mdi/close';

	export let collection: SlimCollection | Collection;

	let templateName = collection.name;
	let templateDescription = collection.description || '';
	let isPublic = false;
	let isSaving = false;

	async function saveTemplate() {
		if (!templateName.trim()) {
			addToast('error', $t('templates.name_required') || 'Template name is required');
			return;
		}

		isSaving = true;
		try {
			const res = await fetch(`/api/collections/${collection.id}/save-as-template/`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					name: templateName,
					description: templateDescription,
					is_public: isPublic
				})
			});

			if (res.ok) {
				const template = await res.json();
				addToast('success', $t('collection.template_saved_success') || 'Template saved successfully');
				dispatch('saved', template);
				close();
			} else {
				const error = await res.json();
				addToast('error', error.error || $t('templates.save_error') || 'Error saving template');
			}
		} catch (e) {
			addToast('error', $t('templates.save_error') || 'Error saving template');
		} finally {
			isSaving = false;
		}
	}

	onMount(async () => {
		modal = document.getElementById('template_modal') as HTMLDialogElement;
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
</script>

<dialog id="template_modal" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div
		class="modal-box w-11/12 max-w-lg p-6 space-y-6"
		role="dialog"
		tabindex="0"
		on:keydown={handleKeydown}
	>
		<!-- Header -->
		<div class="flex items-center justify-between border-b border-base-300 pb-4 mb-4">
			<div class="flex items-center gap-3">
				<div class="p-2 bg-primary/10 rounded-xl">
					<FileDocumentPlus class="w-6 h-6 text-primary" />
				</div>
				<div>
					<h3 class="text-2xl font-bold text-primary">
						{$t('collection.save_as_template') || 'Save as Template'}
					</h3>
					<p class="text-sm text-base-content/60">
						{$t('templates.save_template_desc') || 'Create a reusable template from this collection'}
					</p>
				</div>
			</div>
			<button class="btn btn-ghost btn-sm btn-square" on:click={close}>
				<Clear class="w-5 h-5" />
			</button>
		</div>

		<!-- Form -->
		<div class="space-y-4">
			<!-- Template Name -->
			<div class="form-control">
				<label class="label" for="template-name">
					<span class="label-text font-medium">{$t('templates.template_name') || 'Template Name'}</span>
				</label>
				<input
					id="template-name"
					type="text"
					class="input input-bordered w-full"
					bind:value={templateName}
					placeholder={$t('templates.enter_template_name') || 'Enter template name'}
				/>
			</div>

			<!-- Description -->
			<div class="form-control">
				<label class="label" for="template-description">
					<span class="label-text font-medium">{$t('adventures.description') || 'Description'}</span>
				</label>
				<textarea
					id="template-description"
					class="textarea textarea-bordered w-full h-24"
					bind:value={templateDescription}
					placeholder={$t('templates.enter_description') || 'Enter description (optional)'}
				></textarea>
			</div>

			<!-- Public Toggle -->
			<div class="form-control">
				<label class="label cursor-pointer justify-start gap-3">
					<input type="checkbox" class="toggle toggle-primary" bind:checked={isPublic} />
					<div class="flex flex-col">
						<span class="label-text font-medium">{$t('templates.make_public') || 'Make Public'}</span>
						<span class="label-text-alt text-base-content/60">
							{$t('templates.make_public_description') || 'Allow other users to use this template'}
						</span>
					</div>
				</label>
			</div>

			<!-- Info about what's included -->
			<div class="alert bg-base-200">
				<div>
					<h4 class="font-medium text-sm mb-1">{$t('templates.whats_included') || "What's included"}</h4>
					<ul class="text-xs text-base-content/70 list-disc list-inside space-y-0.5">
						<li>{$t('navbar.locations') || 'Locations'}</li>
						<li>{$t('adventures.notes') || 'Notes'}</li>
						<li>{$t('adventures.checklists') || 'Checklists'}</li>
						<li>{$t('adventures.transportations') || 'Transportations'}</li>
						<li>{$t('adventures.lodging') || 'Lodging'}</li>
					</ul>
					<p class="text-xs text-base-content/50 mt-2 italic">
						{$t('templates.not_included_info')}
					</p>
				</div>
			</div>
		</div>

		<!-- Actions -->
		<div class="pt-4 border-t border-base-300 flex justify-end gap-2">
			<button class="btn btn-ghost" on:click={close}>
				{$t('adventures.cancel') || 'Cancel'}
			</button>
			<button class="btn btn-primary" on:click={saveTemplate} disabled={isSaving}>
				{#if isSaving}
					<span class="loading loading-spinner loading-sm"></span>
				{/if}
				{isSaving ? ($t('adventures.saving') || 'Saving...') : ($t('notes.save') || 'Save')}
			</button>
		</div>
	</div>
	<form method="dialog" class="modal-backdrop">
		<button on:click={close}>close</button>
	</form>
</dialog>
