<script lang="ts">
	import { goto } from '$app/navigation';
	import type { CollectionTemplate, Collection } from '$lib/types';
	import { t } from 'svelte-i18n';
	import { addToast } from '$lib/toasts';

	import Plus from '~icons/mdi/plus';
	import TemplateIcon from '~icons/mdi/file-document-multiple';
	import Eye from '~icons/mdi/eye';
	import EyeOff from '~icons/mdi/eye-off';
	import TrashCan from '~icons/mdi/trashcan';
	import NoteIcon from '~icons/mdi/note-text';
	import ChecklistIcon from '~icons/mdi/checkbox-marked-outline';
	import TransportIcon from '~icons/mdi/airplane';
	import LodgingIcon from '~icons/mdi/bed';
	import LocationIcon from '~icons/mdi/map-marker';
	import DeleteWarning from '$lib/components/DeleteWarning.svelte';

	export let data: any;

	let templates: CollectionTemplate[] = data.props.templates || [];
	let activeView: 'my' | 'public' = 'my';
	let isCreating: string | null = null;
	let isDeleting: boolean = false;
	let templateToDelete: CollectionTemplate | null = null;

	$: myTemplates = templates.filter((t) => t.user === data.user?.uuid);
	$: publicTemplates = templates.filter((t) => t.is_public && t.user !== data.user?.uuid);
	$: currentTemplates = activeView === 'my' ? myTemplates : publicTemplates;

	async function createFromTemplate(template: CollectionTemplate) {
		isCreating = template.id;
		try {
			const res = await fetch(`/api/collection-templates/${template.id}/create-collection/`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				}
			});

			if (res.ok) {
				const newCollection = await res.json();
				addToast('success', $t('templates.collection_created') || 'Collection created from template');
				goto(`/collections/${newCollection.id}`);
			} else {
				const error = await res.json();
				addToast('error', error.error || $t('templates.create_error') || 'Error creating collection');
			}
		} catch (e) {
			addToast('error', $t('templates.create_error') || 'Error creating collection');
		} finally {
			isCreating = null;
		}
	}

	async function deleteTemplate() {
		if (!templateToDelete) return;

		try {
			const res = await fetch(`/api/collection-templates/${templateToDelete.id}/`, {
				method: 'DELETE'
			});

			if (res.ok) {
				templates = templates.filter((t) => t.id !== templateToDelete?.id);
				addToast('success', $t('templates.deleted_success') || 'Template deleted successfully');
			} else {
				const error = await res.json();
				addToast('error', error.error || $t('templates.delete_error') || 'Error deleting template');
			}
		} catch (e) {
			addToast('error', $t('templates.delete_error') || 'Error deleting template');
		} finally {
			templateToDelete = null;
			isDeleting = false;
		}
	}

	function getItemCount(template: CollectionTemplate): { locations: number; notes: number; checklists: number; transportations: number; lodgings: number } {
		const data = template.template_data || {};
		return {
			locations: (data.locations || []).length,
			notes: (data.notes || []).length,
			checklists: (data.checklists || []).length,
			transportations: (data.transportations || []).length,
			lodgings: (data.lodgings || []).length
		};
	}

	function formatDate(dateString: string): string {
		return new Date(dateString).toLocaleDateString(undefined, {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	}
</script>

<svelte:head>
	<title>{$t('templates.title') || 'Collection Templates'}</title>
	<meta name="description" content="Manage your collection templates." />
</svelte:head>

{#if isDeleting && templateToDelete}
	<DeleteWarning
		title={$t('templates.delete_template') || 'Delete Template'}
		button_text={$t('adventures.delete') || 'Delete'}
		description={$t('templates.delete_warning') || 'Are you sure you want to delete this template? This action cannot be undone.'}
		is_warning={true}
		on:close={() => {
			isDeleting = false;
			templateToDelete = null;
		}}
		on:confirm={deleteTemplate}
	/>
{/if}

<div class="min-h-screen bg-gradient-to-br from-base-200 via-base-100 to-base-200">
	<!-- Header Section -->
	<div class="sticky top-0 z-40 bg-base-100/80 backdrop-blur-lg border-b border-base-300">
		<div class="container mx-auto px-6 py-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-3">
					<div class="p-2 bg-primary/10 rounded-xl">
						<TemplateIcon class="w-8 h-8 text-primary" />
					</div>
					<div>
						<h1 class="text-3xl font-bold bg-clip-text text-primary">
							{$t('templates.title') || 'Collection Templates'}
						</h1>
						<p class="text-sm text-base-content/60">
							{currentTemplates.length}
							{activeView === 'my'
								? $t('templates.my_templates') || 'My Templates'
								: $t('templates.public_templates') || 'Public Templates'}
						</p>
					</div>
				</div>

				<!-- View Toggle -->
				<div class="tabs tabs-boxed bg-base-200">
					<button
						class="tab gap-2 {activeView === 'my' ? 'tab-active' : ''}"
						on:click={() => (activeView = 'my')}
					>
						<EyeOff class="w-4 h-4" />
						<span class="hidden sm:inline">{$t('templates.my_templates') || 'My Templates'}</span>
						<div class="badge badge-sm {activeView === 'my' ? 'badge-primary' : 'badge-ghost'}">
							{myTemplates.length}
						</div>
					</button>
					<button
						class="tab gap-2 {activeView === 'public' ? 'tab-active' : ''}"
						on:click={() => (activeView = 'public')}
					>
						<Eye class="w-4 h-4" />
						<span class="hidden sm:inline">{$t('templates.public_templates') || 'Public Templates'}</span>
						<div class="badge badge-sm {activeView === 'public' ? 'badge-primary' : 'badge-ghost'}">
							{publicTemplates.length}
						</div>
					</button>
				</div>
			</div>
		</div>
	</div>

	<!-- Main Content -->
	<div class="container mx-auto px-6 py-8">
		{#if currentTemplates.length === 0}
			<!-- Empty State -->
			<div class="flex flex-col items-center justify-center py-16">
				<div class="p-6 bg-base-200/50 rounded-2xl mb-6">
					<TemplateIcon class="w-16 h-16 text-base-content/30" />
				</div>
				<h3 class="text-xl font-semibold text-base-content/70 mb-2">
					{$t('templates.no_templates') || 'No templates found'}
				</h3>
				<p class="text-base-content/50 text-center max-w-md">
					{activeView === 'my'
						? $t('templates.no_my_templates_desc') || 'Create templates from your collections to reuse their structure.'
						: $t('templates.no_public_templates_desc') || 'No public templates available from other users yet.'}
				</p>
				{#if activeView === 'my'}
					<a href="/collections" class="btn btn-primary btn-wide mt-6 gap-2">
						<Plus class="w-5 h-5" />
						{$t('templates.go_to_collections') || 'Go to Collections'}
					</a>
				{/if}
			</div>
		{:else}
			<!-- Templates Grid -->
			<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
				{#each currentTemplates as template (template.id)}
					{@const counts = getItemCount(template)}
					<div class="card bg-base-100 shadow-lg border border-base-300 hover:shadow-xl transition-all duration-200">
						<div class="card-body p-5">
							<!-- Header -->
							<div class="flex items-start justify-between mb-3">
								<div class="flex items-center gap-3">
									<div class="p-2 bg-primary/10 rounded-lg">
										<TemplateIcon class="w-5 h-5 text-primary" />
									</div>
									<div>
										<h3 class="font-semibold text-lg line-clamp-1">{template.name}</h3>
										<p class="text-xs text-base-content/50">
											{formatDate(template.created_at)}
										</p>
									</div>
								</div>
								<div
									class="tooltip tooltip-left"
									data-tip={template.is_public
										? $t('adventures.public') || 'Public'
										: $t('adventures.private') || 'Private'}
								>
									<div class="badge badge-sm {template.is_public ? 'badge-secondary' : 'badge-ghost'}">
										{#if template.is_public}
											<Eye class="w-3 h-3" />
										{:else}
											<EyeOff class="w-3 h-3" />
										{/if}
									</div>
								</div>
							</div>

							<!-- Description -->
							{#if template.description}
								<p class="text-sm text-base-content/70 line-clamp-2 mb-3">
									{template.description}
								</p>
							{/if}

							<!-- Content Summary -->
							<div class="flex flex-wrap gap-2 mb-4">
								{#if counts.locations > 0}
									<div class="badge badge-outline gap-1">
										<LocationIcon class="w-3 h-3" />
										{counts.locations}
									</div>
								{/if}
								{#if counts.notes > 0}
									<div class="badge badge-outline gap-1">
										<NoteIcon class="w-3 h-3" />
										{counts.notes}
									</div>
								{/if}
								{#if counts.checklists > 0}
									<div class="badge badge-outline gap-1">
										<ChecklistIcon class="w-3 h-3" />
										{counts.checklists}
									</div>
								{/if}
								{#if counts.transportations > 0}
									<div class="badge badge-outline gap-1">
										<TransportIcon class="w-3 h-3" />
										{counts.transportations}
									</div>
								{/if}
								{#if counts.lodgings > 0}
									<div class="badge badge-outline gap-1">
										<LodgingIcon class="w-3 h-3" />
										{counts.lodgings}
									</div>
								{/if}
								{#if counts.locations === 0 && counts.notes === 0 && counts.checklists === 0 && counts.transportations === 0 && counts.lodgings === 0}
									<span class="text-xs text-base-content/50 italic">
										{$t('templates.empty_template') || 'Empty template'}
									</span>
								{/if}
							</div>

							<!-- Actions -->
							<div class="flex gap-2 pt-3 border-t border-base-300">
								<button
									class="btn btn-primary btn-sm flex-1"
									on:click={() => createFromTemplate(template)}
									disabled={isCreating === template.id}
								>
									{#if isCreating === template.id}
										<span class="loading loading-spinner loading-xs"></span>
									{:else}
										<Plus class="w-4 h-4" />
									{/if}
									{$t('templates.create_from_template')}
								</button>
								{#if template.user === data.user?.uuid}
									<button
										class="btn btn-ghost btn-sm btn-square text-error"
										on:click={() => {
											templateToDelete = template;
											isDeleting = true;
										}}
									>
										<TrashCan class="w-4 h-4" />
									</button>
								{/if}
							</div>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
