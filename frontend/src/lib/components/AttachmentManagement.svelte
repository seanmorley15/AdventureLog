<script lang="ts">
	import type { Attachment, User } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	import { t } from 'svelte-i18n';
	import { deserialize } from '$app/forms';

	// Icons
	import TrashIcon from '~icons/mdi/delete';
	import EditIcon from '~icons/mdi/pencil';
	import FileIcon from '~icons/mdi/file-document';
	import AttachmentIcon from '~icons/mdi/attachment';
	import LaunchIcon from '~icons/mdi/open-in-new';
	import CheckIcon from '~icons/mdi/check';
	import CloseIcon from '~icons/mdi/close';
	import LightbubOnIcon from '~icons/mdi/lightbulb-on';

	import { addToast } from '$lib/toasts';
	import StravaGpxList from './transportation/StravaGpxList.svelte';

	

	interface Props {
		// Props
		attachments?: Attachment[];
		itemId?: string;
		contentType?: 'location' | 'lodging' | 'transportation' | '';
		user?: User | null;
		start_date?: string | null;
		end_date?: string | null;
	}

	let {
		attachments = $bindable([]),
		itemId = '',
		contentType = 'location',
		user = null,
		start_date = null,
		end_date = null
	}: Props = $props();

	// Component state
	let attachmentFileInput: HTMLInputElement | undefined = $state();
	let attachmentError: string = $state('');
	let isAttachmentLoading: boolean = $state(false);

	// Attachment state
	let selectedFile: File | null = $state(null);
	let attachmentName: string = $state('');
	let attachmentToEdit: Attachment | null = $state(null);
	let editingAttachmentName: string = $state('');

	// Allowed file types for attachments
	const allowedFileTypes = [
		'.gpx',
		'.kml',
		'.kmz',
		'.pdf',
		'.doc',
		'.docx',
		'.txt',
		'.md',
		'.json',
		'.xml',
		'.csv',
		'.xlsx'
	];

	const dispatch = createEventDispatcher();

	// Helper functions
	function updateAttachmentsList(newAttachment: Attachment) {
		attachments = [...attachments, newAttachment];
		dispatch('attachmentsUpdated', attachments);
	}

	// Attachment event handlers
	function handleAttachmentFileChange(event: Event) {
		const files = (event.target as HTMLInputElement).files;
		if (files && files.length > 0) {
			selectedFile = files[0];
			// Auto-fill attachment name if empty
			if (!attachmentName.trim()) {
				attachmentName = selectedFile.name.split('.')[0];
			}
		} else {
			selectedFile = null;
		}
		attachmentError = '';
	}

	async function uploadAttachment() {
		if (!selectedFile) {
			attachmentError = $t('adventures.no_file_selected');
			return;
		}

		if (!attachmentName.trim()) {
			attachmentError = $t('adventures.attachment_name_required');
			return;
		}

		isAttachmentLoading = true;
		attachmentError = '';

		const formData = new FormData();
		formData.append('file', selectedFile);
		formData.append('name', attachmentName.trim());

		formData.append('object_id', itemId);
		formData.append('content_type', contentType);

		try {
			const res = await fetch('/locations?/attachment', {
				method: 'POST',
				body: formData
			});

			if (res.ok) {
				const newData = deserialize(await res.text()) as { data: Attachment };
				updateAttachmentsList(newData.data);
				addToast('success', $t('adventures.attachment_upload_success'));

				// Reset form
				attachmentName = '';
				selectedFile = null;
				if (attachmentFileInput) {
					attachmentFileInput.value = '';
				}
			} else {
				throw new Error('Upload failed');
			}
		} catch (error) {
			console.error('Attachment upload error:', error);
			attachmentError = $t('adventures.attachment_upload_error');
			addToast('error', $t('adventures.attachment_upload_error'));
		} finally {
			isAttachmentLoading = false;
		}
	}

	function startEditingAttachment(attachment: Attachment) {
		attachmentToEdit = attachment;
		editingAttachmentName = attachment.name;
	}

	function cancelEditingAttachment() {
		attachmentToEdit = null;
		editingAttachmentName = '';
	}

	async function saveAttachmentEdit() {
		if (!attachmentToEdit || !editingAttachmentName.trim()) return;

		try {
			const res = await fetch(`/api/attachments/${attachmentToEdit.id}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					name: editingAttachmentName.trim()
				})
			});

			if (res.ok) {
				attachments = attachments.map((att) =>
					att.id === attachmentToEdit!.id ? { ...att, name: editingAttachmentName.trim() } : att
				);
				dispatch('attachmentsUpdated', attachments);
				addToast('success', $t('adventures.attachment_updated'));
				cancelEditingAttachment();
			} else {
				throw new Error('Failed to update attachment');
			}
		} catch (error) {
			console.error('Error updating attachment:', error);
			addToast('error', $t('adventures.attachment_update_error'));
		}
	}

	async function removeAttachment(attachmentId: string) {
		try {
			const res = await fetch(`/api/attachments/${attachmentId}`, {
				method: 'DELETE'
			});

			if (res.status === 204) {
				attachments = attachments.filter((attachment) => attachment.id !== attachmentId);
				dispatch('attachmentsUpdated', attachments);
				addToast('success', $t('adventures.attachment_removed'));
			} else {
				throw new Error('Failed to remove attachment');
			}
		} catch (error) {
			console.error('Error removing attachment:', error);
			addToast('error', $t('adventures.attachment_remove_error'));
		}
	}
</script>

<div class="card bg-base-100 border border-base-300">
	<div class="card-body p-6">
		<div class="flex items-center gap-3 mb-6">
			<div class="p-2 bg-secondary/10 rounded-lg">
				<AttachmentIcon class="w-5 h-5 text-secondary" />
			</div>
			<h2 class="text-xl font-bold">{$t('adventures.attachment_management')}</h2>
		</div>

		<!-- transportation GPX tip box -->
		{#if contentType === 'transportation'}
			<div class="alert alert-neutral mb-6">
				<div class="flex-1">
					<div class="flex items-center gap-2">
						<LightbubOnIcon class="w-5 h-5" />
						<p class="text-sm">
							{$t('adventures.transportation_gpx_tip')}
						</p>
					</div>
				</div>
			</div>
		{/if}

		<!-- Upload Options -->
		<div class="grid gap-4 mb-6">
			<!-- File Upload -->
			<div class="bg-base-200/40 p-4 rounded-lg border border-base-300">
				<h4 class="font-medium mb-3 text-base-content/80">
					{$t('adventures.upload_attachment')}
				</h4>
				<div class="grid gap-3 md:grid-cols-3">
					<input
						type="file"
						bind:this={attachmentFileInput}
						class="file-input col-span-2 md:col-span-1"
						accept={allowedFileTypes.join(',')}
						disabled={isAttachmentLoading}
						onchange={handleAttachmentFileChange}
					/>
					<input
						type="text"
						bind:value={attachmentName}
						class="input"
						placeholder={$t('adventures.attachment_name')}
						disabled={isAttachmentLoading}
					/>
					<button
						class="btn btn-secondary btn-sm md:btn-md"
						class:loading={isAttachmentLoading}
						disabled={isAttachmentLoading || !selectedFile || !attachmentName.trim()}
						onclick={uploadAttachment}
					>
						{$t('adventures.upload')}
					</button>
				</div>
				{#if contentType === 'transportation'}
					<StravaGpxList {start_date} {end_date} {user} />
				{/if}
				{#if attachmentError}
					<div class="alert alert-error mt-2 py-2">
						<span class="text-sm">{attachmentError}</span>
					</div>
				{/if}
			</div>
		</div>

		<!-- Attachment Gallery -->
		{#if attachments.length > 0}
			<div class="divider">{$t('adventures.current_attachments')}</div>
			<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
				{#each attachments as attachment (attachment.id)}
					<div class="relative group">
						{#if attachmentToEdit?.id === attachment.id}
							<!-- Edit Mode -->
							<div class="bg-warning/10 p-4 rounded-lg border border-warning/30">
								<div class="flex items-center gap-2 mb-3">
									<EditIcon class="w-4 h-4 text-warning" />
									<span class="text-sm font-medium text-warning">Editing</span>
								</div>
								<input
									type="text"
									bind:value={editingAttachmentName}
									class="input input-sm w-full mb-3"
									placeholder="Attachment name"
								/>
								<div class="flex gap-2">
									<button class="btn btn-success btn-xs flex-1" onclick={saveAttachmentEdit}>
										<CheckIcon class="w-3 h-3" />
										Save
									</button>
									<button class="btn btn-ghost btn-xs flex-1" onclick={cancelEditingAttachment}>
										<CloseIcon class="w-3 h-3" />
										{$t('adventures.cancel')}
									</button>
								</div>
							</div>
						{:else}
							<!-- Normal Display -->
							<div
								class="bg-base-200/40 p-4 rounded-lg border border-base-300 hover:border-base-300 transition-colors"
							>
								<div class="flex items-center gap-3 mb-2">
									<div class="p-2 bg-secondary/10 rounded-sm flex items-center justify-center">
										<FileIcon class="w-4 h-4 text-secondary" />
									</div>
									<div class="flex-1 min-w-0">
										{#if attachment.file}
											<a
												href={attachment.file}
												target="_blank"
												rel="noopener noreferrer"
												class="font-medium truncate hover:underline underline-offset-2"
												aria-label="Open attachment in new tab">{attachment.name}</a
											>
										{:else}
											<div class="font-medium truncate">{attachment.name}</div>
										{/if}
										<div class="text-xs text-base-content/60">
											{attachment.extension.toUpperCase()}
										</div>
									</div>
								</div>

								<!-- Attachment Controls -->
								<div class="flex gap-2 mt-3 justify-end">
									<!-- Open in new tab button -->
									{#if attachment.file}
										<a
											href={attachment.file}
											target="_blank"
											rel="noopener noreferrer"
											class="btn btn-xs btn-square neutral-200 hover:bg-neutral-300 text-base-content tooltip tooltip-top"
											data-tip="Open in new tab"
											aria-label="Open attachment in new tab"
										>
											<LaunchIcon class="w-4 h-4" />
										</a>
									{/if}
									<button
										type="button"
										class="btn btn-warning btn-xs btn-square tooltip tooltip-top"
										data-tip="Edit Name"
										onclick={() => startEditingAttachment(attachment)}
									>
										<EditIcon class="w-4 h-4" />
									</button>
									<button
										type="button"
										class="btn btn-error btn-xs btn-square tooltip tooltip-top"
										data-tip="Remove Attachment"
										onclick={() => removeAttachment(attachment.id)}
									>
										<TrashIcon class="w-4 h-4" />
									</button>
								</div>
							</div>
						{/if}
					</div>
				{/each}
			</div>
		{:else}
			<div class="bg-base-200/50 rounded-lg p-8 text-center">
				<div class="text-base-content/60 mb-2">
					{$t('adventures.no_attachments_uploaded_yet')}
				</div>
				<div class="text-sm text-base-content/40">
					{$t('adventures.upload_first_attachment')}
				</div>
			</div>
		{/if}
	</div>
</div>
