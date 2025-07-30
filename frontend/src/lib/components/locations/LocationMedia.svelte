<script lang="ts">
	import type { Attachment, ContentImage } from '$lib/types';
	import { createEventDispatcher, onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import { deserialize } from '$app/forms';

	// Icons
	import InfoIcon from '~icons/mdi/information';
	import Star from '~icons/mdi/star';
	import Crown from '~icons/mdi/crown';
	import SaveIcon from '~icons/mdi/content-save';
	import ArrowLeftIcon from '~icons/mdi/arrow-left';
	import TrashIcon from '~icons/mdi/delete';
	import EditIcon from '~icons/mdi/pencil';
	import FileIcon from '~icons/mdi/file-document';
	import CheckIcon from '~icons/mdi/check';
	import CloseIcon from '~icons/mdi/close';
	import ImageIcon from '~icons/mdi/image';
	import AttachmentIcon from '~icons/mdi/attachment';
	import SwapHorizontalVariantIcon from '~icons/mdi/swap-horizontal-variant';

	import { addToast } from '$lib/toasts';
	import ImmichSelect from '../ImmichSelect.svelte';

	// Props
	export let images: ContentImage[] = [];
	export let attachments: Attachment[] = [];
	export let itemId: string = '';

	// Component state
	let fileInput: HTMLInputElement;
	let attachmentFileInput: HTMLInputElement;
	let url: string = '';
	let imageSearch: string = '';
	let imageError: string = '';
	let wikiImageError: string = '';
	let attachmentError: string = '';
	let immichIntegration: boolean = false;
	let copyImmichLocally: boolean = false;
	let isLoading: boolean = false;
	let isAttachmentLoading: boolean = false;

	// Attachment state
	let selectedFile: File | null = null;
	let attachmentName: string = '';
	let attachmentToEdit: Attachment | null = null;
	let editingAttachmentName: string = '';

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
	function createImageFromData(data: {
		id: string;
		image: string;
		immich_id?: string | null;
	}): ContentImage {
		return {
			id: data.id,
			image: data.image,
			is_primary: false,
			immich_id: data.immich_id || null
		};
	}

	function updateImagesList(newImage: ContentImage) {
		images = [...images, newImage];
	}

	function updateAttachmentsList(newAttachment: Attachment) {
		attachments = [...attachments, newAttachment];
	}

	// API calls
	async function uploadImageToServer(file: File) {
		const formData = new FormData();
		formData.append('image', file);
		formData.append('object_id', itemId);
		formData.append('content_type', 'location');

		try {
			const res = await fetch(`/locations?/image`, {
				method: 'POST',
				body: formData
			});

			if (res.ok) {
				const newData = deserialize(await res.text()) as { data: { id: string; image: string } };
				return createImageFromData(newData.data);
			} else {
				throw new Error('Upload failed');
			}
		} catch (error) {
			console.error('Upload error:', error);
			return null;
		}
	}

	async function fetchImageFromUrl(imageUrl: string): Promise<Blob | null> {
		try {
			const res = await fetch(imageUrl);
			if (!res.ok) throw new Error('Failed to fetch image');
			return await res.blob();
		} catch (error) {
			console.error('Fetch error:', error);
			return null;
		}
	}

	// Image event handlers
	async function handleMultipleFiles(event: Event) {
		const files = (event.target as HTMLInputElement).files;
		if (!files) return;

		isLoading = true;
		imageError = '';

		try {
			for (const file of files) {
				const newImage = await uploadImageToServer(file);
				if (newImage) {
					updateImagesList(newImage);
				}
			}
			addToast('success', $t('adventures.image_upload_success'));
		} catch (error) {
			addToast('error', $t('adventures.image_upload_error'));
			imageError = $t('adventures.image_upload_error');
		} finally {
			isLoading = false;
			if (fileInput) fileInput.value = '';
		}
	}

	async function handleUrlUpload() {
		if (!url.trim()) return;

		isLoading = true;
		imageError = '';

		try {
			const blob = await fetchImageFromUrl(url);
			if (!blob) {
				imageError = $t('adventures.no_image_url');
				return;
			}

			const file = new File([blob], 'image.jpg', { type: 'image/jpeg' });
			const newImage = await uploadImageToServer(file);

			if (newImage) {
				updateImagesList(newImage);
				addToast('success', $t('adventures.image_upload_success'));
				url = '';
			} else {
				throw new Error('Upload failed');
			}
		} catch (error) {
			imageError = $t('adventures.image_fetch_failed');
			addToast('error', $t('adventures.image_upload_error'));
		} finally {
			isLoading = false;
		}
	}

	async function handleWikiImageSearch() {
		if (!imageSearch.trim()) return;

		isLoading = true;
		wikiImageError = '';

		try {
			const res = await fetch(`/api/generate/img/?name=${encodeURIComponent(imageSearch)}`);
			const data = await res.json();

			if (!res.ok || !data.source) {
				wikiImageError = $t('adventures.image_fetch_failed');
				return;
			}

			const blob = await fetchImageFromUrl(data.source);
			if (!blob) {
				wikiImageError = $t('adventures.image_fetch_failed');
				return;
			}

			const file = new File([blob], `${imageSearch}.jpg`, { type: 'image/jpeg' });
			const newImage = await uploadImageToServer(file);

			if (newImage) {
				updateImagesList(newImage);
				addToast('success', $t('adventures.image_upload_success'));
				imageSearch = '';
			} else {
				throw new Error('Upload failed');
			}
		} catch (error) {
			wikiImageError = $t('adventures.wiki_image_error');
			addToast('error', $t('adventures.image_upload_error'));
		} finally {
			isLoading = false;
		}
	}

	async function makePrimaryImage(imageId: string) {
		try {
			const res = await fetch(`/api/images/${imageId}/toggle_primary`, {
				method: 'POST'
			});

			if (res.ok) {
				images = images.map((image) => ({
					...image,
					is_primary: image.id === imageId
				}));
				addToast('success', 'Primary image updated');
			} else {
				throw new Error('Failed to update primary image');
			}
		} catch (error) {
			console.error('Error in makePrimaryImage:', error);
			addToast('error', 'Failed to update primary image');
		}
	}

	async function removeImage(imageId: string) {
		try {
			const res = await fetch(`/api/images/${imageId}/image_delete`, {
				method: 'POST'
			});

			if (res.status === 204) {
				images = images.filter((image) => image.id !== imageId);
				addToast('success', 'Image removed');
			} else {
				throw new Error('Failed to remove image');
			}
		} catch (error) {
			console.error('Error removing image:', error);
			addToast('error', 'Failed to remove image');
		}
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
		formData.append('location', itemId);
		formData.append('name', attachmentName.trim());

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
				addToast('success', $t('adventures.attachment_removed'));
			} else {
				throw new Error('Failed to remove attachment');
			}
		} catch (error) {
			console.error('Error removing attachment:', error);
			addToast('error', $t('adventures.attachment_remove_error'));
		}
	}

	// Navigation handlers
	function handleBack() {
		dispatch('back');
	}

	function handleNext() {
		dispatch('next');
	}

	function handleImmichImageSaved(event: CustomEvent) {
		const newImage = createImageFromData(event.detail);
		updateImagesList(newImage);
		addToast('success', $t('adventures.image_upload_success'));
	}

	// Lifecycle
	onMount(async () => {
		try {
			const res = await fetch('/api/integrations/immich/');

			if (res.ok) {
				const data = await res.json();
				if (data.id) {
					immichIntegration = true;
					copyImmichLocally = data.copy_locally || false;
				}
			} else if (res.status !== 404) {
				addToast('error', $t('immich.integration_fetch_error'));
			}
		} catch (error) {
			console.error('Error checking Immich integration:', error);
		}
	});
</script>

<div class="min-h-screen bg-gradient-to-br from-base-200/30 via-base-100 to-primary/5 p-6">
	<div class="max-w-full mx-auto space-y-6">
		<!-- Image Management Section -->
		<div class="card bg-base-100 border border-base-300 shadow-lg">
			<div class="card-body p-6">
				<div class="flex items-center gap-3 mb-6">
					<div class="p-2 bg-primary/10 rounded-lg">
						<ImageIcon class="w-5 h-5 text-primary" />
					</div>
					<h2 class="text-xl font-bold">Image Management</h2>
				</div>

				<!-- Upload Options Grid -->
				<div class="grid gap-4 lg:grid-cols-2 mb-6">
					<!-- File Upload -->
					<div class="bg-base-50 p-4 rounded-lg border border-base-200">
						<h4 class="font-medium mb-3 text-base-content/80">
							{$t('adventures.upload_from_device')}
						</h4>
						<input
							type="file"
							bind:this={fileInput}
							class="file-input file-input-bordered w-full"
							accept="image/*"
							multiple
							disabled={isLoading}
							on:change={handleMultipleFiles}
						/>
					</div>

					<!-- URL Upload -->
					<div class="bg-base-50 p-4 rounded-lg border border-base-200">
						<h4 class="font-medium mb-3 text-base-content/80">
							{$t('adventures.upload_from_url')}
						</h4>
						<div class="flex gap-2">
							<input
								type="url"
								bind:value={url}
								class="input input-bordered flex-1"
								placeholder="https://example.com/image.jpg"
								disabled={isLoading}
							/>
							<button
								class="btn btn-primary btn-sm"
								class:loading={isLoading}
								disabled={isLoading || !url.trim()}
								on:click={handleUrlUpload}
							>
								{$t('adventures.fetch_image')}
							</button>
						</div>
						{#if imageError}
							<div class="alert alert-error mt-2 py-2">
								<span class="text-sm">{imageError}</span>
							</div>
						{/if}
					</div>

					<!-- Wikipedia Search -->
					<div class="bg-base-50 p-4 rounded-lg border border-base-200">
						<h4 class="font-medium mb-3 text-base-content/80">
							{$t('adventures.wikipedia')}
						</h4>
						<div class="flex gap-2">
							<input
								type="text"
								bind:value={imageSearch}
								class="input input-bordered flex-1"
								placeholder="Search Wikipedia for images"
								disabled={isLoading}
							/>
							<button
								class="btn btn-primary btn-sm"
								class:loading={isLoading}
								disabled={isLoading || !imageSearch.trim()}
								on:click={handleWikiImageSearch}
							>
								{$t('adventures.fetch_image')}
							</button>
						</div>
						{#if wikiImageError}
							<div class="alert alert-error mt-2 py-2">
								<span class="text-sm">{wikiImageError}</span>
							</div>
						{/if}
					</div>

					<!-- Immich Integration -->
					{#if immichIntegration}
						<div class="bg-base-50 p-4 rounded-lg border border-base-200">
							<h4 class="font-medium mb-3 text-base-content/80">Immich Integration</h4>
							<ImmichSelect
								objectId={itemId}
								contentType="location"
								{copyImmichLocally}
								on:fetchImage={(e) => {
									url = e.detail;
									handleUrlUpload();
								}}
								on:remoteImmichSaved={handleImmichImageSaved}
							/>
						</div>
					{/if}
				</div>

				<!-- Image Gallery -->
				{#if images.length > 0}
					<div class="divider">Current Images</div>
					<div class="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
						{#each images as image (image.id)}
							<div class="relative group">
								<div
									class="aspect-square overflow-hidden rounded-lg bg-base-200 border border-base-300"
								>
									<img
										src={image.image}
										alt="Uploaded content"
										class="w-full h-full object-cover transition-transform group-hover:scale-105"
										loading="lazy"
									/>
								</div>

								<!-- Image Controls Overlay -->
								<div
									class="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-all duration-200 rounded-lg flex items-center justify-center gap-2"
								>
									{#if !image.is_primary}
										<button
											type="button"
											class="btn btn-success btn-sm tooltip tooltip-top"
											data-tip="Make Primary"
											on:click={() => makePrimaryImage(image.id)}
										>
											<Star class="h-4 w-4" />
										</button>
									{/if}

									<button
										type="button"
										class="btn btn-error btn-sm tooltip tooltip-top"
										data-tip="Remove Image"
										on:click={() => removeImage(image.id)}
									>
										<TrashIcon class="h-4 w-4" />
									</button>
								</div>

								<!-- Primary Badge -->
								{#if image.is_primary}
									<div
										class="absolute top-2 left-2 bg-warning text-warning-content rounded-full p-1 shadow-lg"
									>
										<Crown class="h-4 w-4" />
									</div>
								{/if}
							</div>
						{/each}
					</div>
				{:else}
					<div class="bg-base-200/50 rounded-lg p-8 text-center">
						<div class="text-base-content/60 mb-2">No images uploaded yet</div>
						<div class="text-sm text-base-content/40">
							Upload your first image using one of the options above
						</div>
					</div>
				{/if}
			</div>
		</div>

		<!-- Attachment Management Section -->
		<div class="card bg-base-100 border border-base-300 shadow-lg">
			<div class="card-body p-6">
				<div class="flex items-center gap-3 mb-6">
					<div class="p-2 bg-secondary/10 rounded-lg">
						<AttachmentIcon class="w-5 h-5 text-secondary" />
					</div>
					<h2 class="text-xl font-bold">Attachment Management</h2>
				</div>

				<!-- Upload Options -->
				<div class="grid gap-4 mb-6">
					<!-- File Upload -->
					<div class="bg-base-50 p-4 rounded-lg border border-base-200">
						<h4 class="font-medium mb-3 text-base-content/80">
							{$t('adventures.upload_attachment')}
						</h4>
						<div class="grid gap-3 md:grid-cols-3">
							<input
								type="file"
								bind:this={attachmentFileInput}
								class="file-input file-input-bordered col-span-2 md:col-span-1"
								accept={allowedFileTypes.join(',')}
								disabled={isAttachmentLoading}
								on:change={handleAttachmentFileChange}
							/>
							<input
								type="text"
								bind:value={attachmentName}
								class="input input-bordered"
								placeholder={$t('adventures.attachment_name')}
								disabled={isAttachmentLoading}
							/>
							<button
								class="btn btn-secondary btn-sm md:btn-md"
								class:loading={isAttachmentLoading}
								disabled={isAttachmentLoading || !selectedFile || !attachmentName.trim()}
								on:click={uploadAttachment}
							>
								{$t('adventures.upload')}
							</button>
						</div>
						{#if attachmentError}
							<div class="alert alert-error mt-2 py-2">
								<span class="text-sm">{attachmentError}</span>
							</div>
						{/if}
					</div>

					<!-- File Type Info -->
					<div class="alert alert-info">
						<InfoIcon class="h-5 w-5" />
						<div>
							<div class="text-sm font-medium">Supported file types:</div>
							<div class="text-xs text-base-content/70 mt-1">
								GPX, KML, PDF, DOC, TXT, JSON, CSV, XLSX and more
							</div>
						</div>
					</div>
				</div>

				<!-- Attachment Gallery -->
				{#if attachments.length > 0}
					<div class="divider">Current Attachments</div>
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
											class="input input-bordered input-sm w-full mb-3"
											placeholder="Attachment name"
										/>
										<div class="flex gap-2">
											<button class="btn btn-success btn-xs flex-1" on:click={saveAttachmentEdit}>
												<CheckIcon class="w-3 h-3" />
												Save
											</button>
											<button
												class="btn btn-ghost btn-xs flex-1"
												on:click={cancelEditingAttachment}
											>
												<CloseIcon class="w-3 h-3" />
												Cancel
											</button>
										</div>
									</div>
								{:else}
									<!-- Normal Display -->
									<div
										class="bg-base-50 p-4 rounded-lg border border-base-200 hover:border-base-300 transition-colors"
									>
										<div class="flex items-center gap-3 mb-2">
											<div class="p-2 bg-secondary/10 rounded">
												<FileIcon class="w-4 h-4 text-secondary" />
											</div>
											<div class="flex-1 min-w-0">
												<div class="font-medium truncate">{attachment.name}</div>
												<div class="text-xs text-base-content/60">
													{attachment.extension.toUpperCase()}
												</div>
											</div>
										</div>

										<!-- Attachment Controls -->
										<div class="flex gap-2 mt-3 justify-end">
											<button
												type="button"
												class="btn btn-warning btn-xs btn-square tooltip tooltip-top"
												data-tip="Edit Name"
												on:click={() => startEditingAttachment(attachment)}
											>
												<EditIcon class="w-3 h-3" />
											</button>
											<button
												type="button"
												class="btn btn-error btn-xs btn-square tooltip tooltip-top"
												data-tip="Remove Attachment"
												on:click={() => removeAttachment(attachment.id)}
											>
												<TrashIcon class="w-3 h-3" />
											</button>
										</div>
									</div>
								{/if}
							</div>
						{/each}
					</div>
				{:else}
					<div class="bg-base-200/50 rounded-lg p-8 text-center">
						<div class="text-base-content/60 mb-2">No attachments uploaded yet</div>
						<div class="text-sm text-base-content/40">
							Upload your first attachment using the options above
						</div>
					</div>
				{/if}
			</div>
		</div>

		<!-- Trails Managment -->
		<div class="card bg-base-100 border border-base-300 shadow-lg">
			<div class="card-body p-6">
				<div class="flex items-center gap-3 mb-6">
					<div class="p-2 bg-accent/10 rounded-lg">
						<SwapHorizontalVariantIcon class="w-5 h-5 text-accent" />
					</div>
					<h2 class="text-xl font-bold">Trails Management</h2>
				</div>
				<p class="text-base-content/70 mb-4">
					You can manage trails associated with this location in the Trails section.
				</p>
				<p class="text-sm text-base-content/50">
					Coming soon: Create, edit, and delete trails directly from this section.
				</p>
			</div>
		</div>

		<!-- Action Buttons -->
		<div class="flex gap-3 justify-end pt-4">
			<button class="btn btn-neutral-200 gap-2" on:click={handleBack}>
				<ArrowLeftIcon class="w-5 h-5" />
				Back
			</button>

			<button class="btn btn-primary gap-2" on:click={handleNext}>
				<SaveIcon class="w-5 h-5" />
				Next
			</button>
		</div>
	</div>
</div>
