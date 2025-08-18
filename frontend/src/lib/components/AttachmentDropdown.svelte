<script lang="ts">
	import type { Checklist, Lodging, Note, Transportation } from '$lib/types';
	import { deserialize } from '$app/forms';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { t } from 'svelte-i18n';
	import { addToast } from '$lib/toasts';

	export let object: Lodging | Transportation;
	export let objectType: 'lodging' | 'transportation' | 'note' | 'checklist';
	export let isAttachmentsUploading: boolean = false;

	let attachmentInput: HTMLInputElement;
	let attachmentFiles: File[] = [];
	let editingAttachment: { id: string; name: string } | null = null;

	function handleAttachmentChange(event: Event) {
		const target = event.target as HTMLInputElement;
		if (target?.files) {
			attachmentFiles = Array.from(target.files);
			console.log('Attachments selected:', attachmentFiles.length);

			if (object.id) {
				// If object exists, upload immediately
				uploadAttachments();
			}
		}
	}

	// Watch for external trigger to upload attachments
	$: {
		if (isAttachmentsUploading && attachmentFiles.length > 0 && object.id) {
			// Immediately clear the trigger to prevent infinite loop
			const filesToUpload = [...attachmentFiles];
			attachmentFiles = []; // Clear immediately
			if (attachmentInput) {
				attachmentInput.value = '';
			}
			uploadAttachmentsFromList(filesToUpload);
		}
	}

	async function uploadAttachments() {
		if (attachmentFiles.length === 0) {
			isAttachmentsUploading = false;
			return;
		}

		const filesToUpload = [...attachmentFiles];
		// Clear immediately to prevent re-triggering
		attachmentFiles = [];
		if (attachmentInput) {
			attachmentInput.value = '';
		}

		await uploadAttachmentsFromList(filesToUpload);
	}

	async function uploadAttachmentsFromList(files: File[]) {
		if (files.length === 0) {
			isAttachmentsUploading = false;
			return;
		}

		try {
			// Upload all attachments concurrently
			const uploadPromises = files.map((file) => uploadAttachment(file));
			await Promise.all(uploadPromises);
		} catch (error) {
		} finally {
			isAttachmentsUploading = false;
		}
	}

	async function uploadAttachment(file: File): Promise<void> {
		let formData = new FormData();
		formData.append('file', file);
		formData.append('object_id', object.id);
		formData.append('content_type', objectType);

		let res = await fetch(`/locations?/attachment`, {
			method: 'POST',
			body: formData
		});

		if (res.ok) {
			let newData = deserialize(await res.text()) as {
				data: {
					id: string;
					file: string;
					name: string;
					extension: string;
					size: number;
				};
			};
			let newAttachment = {
				id: newData.data.id,
				file: newData.data.file,
				name: newData.data.name,
				extension: newData.data.extension,
				size: newData.data.size,
				user: '',
				geojson: null
			};
			object.attachments = [...(object.attachments || []), newAttachment];
		} else {
			throw new Error(`Failed to upload ${file.name}`);
		}
	}

	async function removeAttachment(id: string) {
		let res = await fetch(`/api/attachments/${id}/`, {
			method: 'DELETE'
		});
		if (res.status === 204) {
			object.attachments = object.attachments.filter(
				(attachment: { id: string }) => attachment.id !== id
			);
			addToast('success', $t('adventures.attachment_removed_success'));
		} else {
			addToast('error', $t('adventures.attachment_removed_error'));
			console.error('Error removing attachment:', await res.text());
		}
	}

	async function updateAttachmentName(attachmentId: string, newName: string) {
		let res = await fetch(`/api/attachments/${attachmentId}/`, {
			method: 'PATCH',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ name: newName })
		});

		if (res.ok) {
			object.attachments = object.attachments.map((attachment) => {
				if (attachment.id === attachmentId) {
					return { ...attachment, name: newName };
				}
				return attachment;
			});
			editingAttachment = null;
		} else {
		}
	}

	function startEditingName(attachment: { id: string; name: string }) {
		editingAttachment = { id: attachment.id, name: attachment.name };
	}

	function cancelEditingName() {
		editingAttachment = null;
	}

	function handleNameKeydown(event: KeyboardEvent, attachmentId: string) {
		if (event.key === 'Enter') {
			updateAttachmentName(attachmentId, editingAttachment?.name || '');
		} else if (event.key === 'Escape') {
			cancelEditingName();
		}
	}

	function getFileIcon(filename: string): string {
		const extension = filename.toLowerCase().split('.').pop() || '';

		switch (extension) {
			case 'pdf':
				return 'M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9.5 11.5c0 .83-.67 1.5-1.5 1.5s-1.5-.67-1.5-1.5.67-1.5 1.5-1.5 1.5.67 1.5 1.5zM17 17H7l3-3.99 2 2.67L16 12l1 5z';
			case 'doc':
			case 'docx':
				return 'M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z';
			case 'xls':
			case 'xlsx':
				return 'M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20M8.93,12.22H10.66L12.03,14.71L13.4,12.22H15.13L13.15,15.31L15.13,18.4H13.4L12.03,15.91L10.66,18.4H8.93L10.91,15.31L8.93,12.22Z';
			case 'txt':
				return 'M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z';
			case 'jpg':
			case 'jpeg':
			case 'png':
			case 'gif':
				return 'M19,3H5C3.89,3 3,3.89 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V5C21,3.89 20.1,3 19,3M19,19H5V5H19V19M13.96,12.29L11.21,15.83L9.25,13.47L6.5,17H17.5L13.96,12.29Z';
			default:
				return 'M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z';
		}
	}

	function formatFileSize(bytes: number): string {
		if (bytes === 0) return '0 Bytes';
		const k = 1024;
		const sizes = ['Bytes', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
	}

	// Export function to check if attachments are ready to upload
	export function hasAttachmentsToUpload(): boolean {
		return attachmentFiles.length > 0;
	}
</script>

<div
	class="collapse collapse-plus bg-base-200/50 border border-base-300/50 mb-6 rounded-2xl overflow-hidden"
>
	<input type="checkbox" />
	<div class="collapse-title text-xl font-semibold bg-gradient-to-r from-primary/10 to-primary/5">
		<div class="flex items-center gap-3">
			<div class="p-2 bg-primary/10 rounded-lg">
				<svg class="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
					/>
				</svg>
			</div>
			{$t('adventures.attachments')}
			{#if isAttachmentsUploading}
				<span class="loading loading-spinner loading-sm text-primary"></span>
			{/if}
		</div>
	</div>
	<div class="collapse-content bg-base-100/50 pt-4 p-6">
		<div class="form-control">
			<label class="label" for="attachment">
				<span class="label-text font-medium">{$t('adventures.upload_attachment')}</span>
			</label>
			<input
				type="file"
				id="attachment"
				name="attachment"
				multiple
				bind:this={attachmentInput}
				on:change={handleAttachmentChange}
				class="file-input file-input-bordered file-input-primary w-full bg-base-100/80 focus:bg-base-100"
				disabled={isAttachmentsUploading}
			/>
		</div>

		{#if attachmentFiles.length > 0 && !object.id}
			<div class="mt-4">
				<h4 class="font-semibold text-base-content mb-2">
					{$t('adventures.selected_attachments')} ({attachmentFiles.length})
				</h4>
				<div class="alert alert-info">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						class="stroke-current shrink-0 w-6 h-6"
						><path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
						></path></svg
					>
					<span>{$t('adventures.attachments_upload_info')} {objectType}</span>
				</div>
				<div class="space-y-2 mt-3">
					{#each attachmentFiles as file}
						<div class="flex items-center gap-3 p-3 bg-base-200/60 rounded-lg">
							<div class="p-2 bg-secondary/20 rounded-lg">
								<svg class="w-4 h-4 text-secondary" fill="currentColor" viewBox="0 0 24 24">
									<path d={getFileIcon(file.name)} />
								</svg>
							</div>
							<div class="flex-1 min-w-0">
								<p class="text-sm font-medium text-base-content truncate">
									{file.name}
								</p>
								<p class="text-xs text-base-content/60">
									{formatFileSize(file.size)}
								</p>
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		{#if object.id}
			<div class="divider my-6"></div>

			<!-- Current Attachments -->
			<div class="space-y-4">
				<h4 class="font-semibold text-lg">{$t('adventures.my_attachments')}</h4>

				{#if object.attachments && object.attachments.length > 0}
					<div class="space-y-3">
						{#each object.attachments as attachment}
							<div
								class="group relative flex items-center gap-4 p-4 bg-base-200/60 hover:bg-base-200 rounded-xl border border-base-300/50 transition-all duration-200 hover:shadow-sm"
							>
								<div class="p-3 bg-secondary/20 rounded-lg">
									<svg class="w-6 h-6 text-secondary" fill="currentColor" viewBox="0 0 24 24">
										<path d={getFileIcon(attachment.name || attachment.file)} />
									</svg>
								</div>

								<div class="flex-1 min-w-0">
									{#if editingAttachment?.id === attachment.id}
										<div class="flex items-center gap-2">
											<!-- svelte-ignore a11y-autofocus -->
											<input
												type="text"
												bind:value={editingAttachment.name}
												on:keydown={(e) => handleNameKeydown(e, attachment.id)}
												class="input input-sm input-bordered flex-1 bg-base-100"
												placeholder="Enter attachment name"
												autofocus
											/>
											<button
												type="button"
												class="btn btn-success btn-sm"
												on:click={() =>
													updateAttachmentName(attachment.id, editingAttachment?.name || '')}
											>
												<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														stroke-width="2"
														d="M5 13l4 4L19 7"
													/>
												</svg>
											</button>
											<button
												type="button"
												class="btn btn-ghost btn-sm"
												on:click={cancelEditingName}
											>
												<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														stroke-width="2"
														d="M6 18L18 6M6 6l12 12"
													/>
												</svg>
											</button>
										</div>
									{:else}
										<div class="flex items-center gap-2">
											<h5 class="text-sm font-semibold text-base-content truncate flex-1">
												{attachment.name || attachment.file.split('/').pop() || 'Untitled'}
											</h5>
											<button
												type="button"
												class="btn btn-ghost btn-xs opacity-0 group-hover:opacity-100 transition-opacity"
												on:click={() => startEditingName(attachment)}
												title="Edit name"
											>
												<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														stroke-width="2"
														d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
													/>
												</svg>
											</button>
										</div>
									{/if}
								</div>

								<div class="flex items-center gap-2">
									<a
										href={attachment.file}
										target="_blank"
										rel="noopener noreferrer"
										class="btn btn-ghost btn-sm opacity-60 group-hover:opacity-100 transition-opacity"
										title="Download"
									>
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
											/>
										</svg>
									</a>

									<button
										type="button"
										class="btn btn-error btn-sm opacity-0 group-hover:opacity-100 transition-opacity"
										on:click={() => removeAttachment(attachment.id)}
										title="Remove"
									>
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
											/>
										</svg>
									</button>
								</div>
							</div>
						{/each}
					</div>
				{:else}
					<div class="text-center py-8">
						<div class="text-base-content/60 text-lg mb-2">
							{$t('adventures.no_attachments')}
						</div>
						<p class="text-sm text-base-content/40">{$t('adventures.no_attachments_desc')}</p>
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>
