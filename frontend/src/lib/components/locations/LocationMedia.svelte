<script lang="ts">
	import type { Attachment, ContentImage, Trail } from '$lib/types';
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
	import LinkIcon from '~icons/mdi/link';
	import PlusIcon from '~icons/mdi/plus';

	import { addToast } from '$lib/toasts';
	import ImmichSelect from '../ImmichSelect.svelte';

	// Props
	export let images: ContentImage[] = [];
	export let attachments: Attachment[] = [];
	export let trails: Trail[] = [];
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

	// Trail state
	let trailName: string = '';
	let trailLink: string = '';
	let trailWandererId: string = '';
	let trailError: string = '';
	let isTrailLoading: boolean = false;
	let trailToEdit: Trail | null = null;
	let editingTrailName: string = '';
	let editingTrailLink: string = '';
	let editingTrailWandererId: string = '';
	let showAddTrailForm: boolean = false;

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

	function updateTrailsList(newTrail: Trail) {
		trails = [...trails, newTrail];
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

	// Trail event handlers
	function validateTrailForm(): boolean {
		if (!trailName.trim()) {
			trailError = 'Trail name is required';
			return false;
		}

		const hasLink = trailLink.trim() !== '';
		const hasWandererId = trailWandererId.trim() !== '';

		if (hasLink && hasWandererId) {
			trailError = 'Cannot have both a link and a Wanderer ID. Provide only one.';
			return false;
		}

		if (!hasLink && !hasWandererId) {
			trailError = 'You must provide either a link or a Wanderer ID.';
			return false;
		}

		trailError = '';
		return true;
	}

	async function createTrail() {
		if (!validateTrailForm()) return;

		isTrailLoading = true;

		const trailData = {
			name: trailName.trim(),
			location: itemId,
			link: trailLink.trim() || null,
			wanderer_id: trailWandererId.trim() || null
		};

		try {
			const res = await fetch('/api/trails/', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(trailData)
			});

			if (res.ok) {
				const newTrail = await res.json();
				updateTrailsList(newTrail);
				addToast('success', 'Trail created successfully');
				resetTrailForm();
			} else {
				const errorData = await res.json();
				throw new Error(errorData.message || 'Failed to create trail');
			}
		} catch (error) {
			console.error('Trail creation error:', error);
			trailError = error instanceof Error ? error.message : 'Failed to create trail';
			addToast('error', 'Failed to create trail');
		} finally {
			isTrailLoading = false;
		}
	}

	function resetTrailForm() {
		trailName = '';
		trailLink = '';
		trailWandererId = '';
		trailError = '';
		showAddTrailForm = false;
	}

	function startEditingTrail(trail: Trail) {
		trailToEdit = trail;
		editingTrailName = trail.name;
		editingTrailLink = trail.link || '';
		editingTrailWandererId = trail.wanderer_id || '';
	}

	function cancelEditingTrail() {
		trailToEdit = null;
		editingTrailName = '';
		editingTrailLink = '';
		editingTrailWandererId = '';
	}

	function validateEditTrailForm(): boolean {
		if (!editingTrailName.trim()) {
			return false;
		}

		const hasLink = editingTrailLink.trim() !== '';
		const hasWandererId = editingTrailWandererId.trim() !== '';

		if (hasLink && hasWandererId) {
			return false;
		}

		if (!hasLink && !hasWandererId) {
			return false;
		}

		return true;
	}

	async function saveTrailEdit() {
		if (!trailToEdit || !validateEditTrailForm()) return;

		const trailData = {
			name: editingTrailName.trim(),
			link: editingTrailLink.trim() || null,
			wanderer_id: editingTrailWandererId.trim() || null
		};

		try {
			const res = await fetch(`/api/trails/${trailToEdit.id}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(trailData)
			});

			if (res.ok) {
				const updatedTrail = await res.json();
				trails = trails.map((trail) => (trail.id === trailToEdit!.id ? updatedTrail : trail));
				addToast('success', 'Trail updated successfully');
				cancelEditingTrail();
			} else {
				throw new Error('Failed to update trail');
			}
		} catch (error) {
			console.error('Error updating trail:', error);
			addToast('error', 'Failed to update trail');
		}
	}

	async function removeTrail(trailId: string) {
		try {
			const res = await fetch(`/api/trails/${trailId}`, {
				method: 'DELETE'
			});

			if (res.status === 204) {
				trails = trails.filter((trail) => trail.id !== trailId);
				addToast('success', 'Trail removed successfully');
			} else {
				throw new Error('Failed to remove trail');
			}
		} catch (error) {
			console.error('Error removing trail:', error);
			addToast('error', 'Failed to remove trail');
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

		<!-- Trails Management -->
		<div class="card bg-base-100 border border-base-300 shadow-lg">
			<div class="card-body p-6">
				<div class="flex items-center justify-between mb-6">
					<div class="flex items-center gap-3">
						<div class="p-2 bg-accent/10 rounded-lg">
							<SwapHorizontalVariantIcon class="w-5 h-5 text-accent" />
						</div>
						<h2 class="text-xl font-bold">Trails Management</h2>
					</div>
					<button
						class="btn btn-accent btn-sm gap-2"
						on:click={() => (showAddTrailForm = !showAddTrailForm)}
					>
						<PlusIcon class="w-4 h-4" />
						Add Trail
					</button>
				</div>

				<div class="text-sm text-base-content/60 mb-4">
					Manage trails associated with this location. Trails can be linked to external services
					like AllTrails or referenced by Wanderer ID.
				</div>

				<!-- Add Trail Form -->
				{#if showAddTrailForm}
					<div class="bg-accent/5 p-4 rounded-lg border border-accent/20 mb-6">
						<h4 class="font-medium mb-3 text-accent">Add New Trail</h4>
						<div class="grid gap-3">
							<input
								type="text"
								bind:value={trailName}
								class="input input-bordered"
								placeholder="Trail name"
								disabled={isTrailLoading}
							/>
							<input
								type="url"
								bind:value={trailLink}
								class="input input-bordered"
								placeholder="External link (e.g., AllTrails, Trailforks)"
								disabled={isTrailLoading || trailWandererId.trim() !== ''}
							/>
							<div class="text-center text-sm text-base-content/60">OR</div>
							<input
								type="text"
								bind:value={trailWandererId}
								class="input input-bordered"
								placeholder="Wanderer Trail ID"
								disabled={isTrailLoading || trailLink.trim() !== ''}
							/>
							{#if trailError}
								<div class="alert alert-error py-2">
									<span class="text-sm">{trailError}</span>
								</div>
							{/if}
							<div class="flex gap-2 justify-end">
								<button
									class="btn btn-ghost btn-sm"
									disabled={isTrailLoading}
									on:click={resetTrailForm}
								>
									Cancel
								</button>
								<button
									class="btn btn-accent btn-sm"
									class:loading={isTrailLoading}
									disabled={isTrailLoading ||
										!trailName.trim() ||
										(!trailLink.trim() && !trailWandererId.trim())}
									on:click={createTrail}
								>
									Create Trail
								</button>
							</div>
						</div>
					</div>
				{/if}

				<!-- Trails Gallery -->
				{#if trails.length > 0}
					<div class="divider">Current Trails</div>
					<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
						{#each trails as trail (trail.id)}
							<div class="relative group">
								{#if trailToEdit?.id === trail.id}
									<!-- Edit Mode -->
									<div class="bg-warning/10 p-4 rounded-lg border border-warning/30">
										<div class="flex items-center gap-2 mb-3">
											<EditIcon class="w-4 h-4 text-warning" />
											<span class="text-sm font-medium text-warning">Editing Trail</span>
										</div>
										<div class="grid gap-3">
											<input
												type="text"
												bind:value={editingTrailName}
												class="input input-bordered input-sm"
												placeholder="Trail name"
											/>
											<input
												type="url"
												bind:value={editingTrailLink}
												class="input input-bordered input-sm"
												placeholder="External link"
												disabled={editingTrailWandererId.trim() !== ''}
											/>
											<div class="text-center text-xs text-base-content/60">OR</div>
											<input
												type="text"
												bind:value={editingTrailWandererId}
												class="input input-bordered input-sm"
												placeholder="Wanderer Trail ID"
												disabled={editingTrailLink.trim() !== ''}
											/>
										</div>
										<div class="flex gap-2 mt-3">
											<button
												class="btn btn-success btn-xs flex-1"
												disabled={!validateEditTrailForm()}
												on:click={saveTrailEdit}
											>
												<CheckIcon class="w-3 h-3" />
												Save
											</button>
											<button class="btn btn-ghost btn-xs flex-1" on:click={cancelEditingTrail}>
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
										<div class="flex items-center gap-3 mb-3">
											<div class="p-2 bg-accent/10 rounded">
												{#if trail.wanderer_id}
													<Star class="w-4 h-4 text-accent" />
												{:else}
													<LinkIcon class="w-4 h-4 text-accent" />
												{/if}
											</div>
											<div class="flex-1 min-w-0">
												<div class="font-medium truncate">{trail.name}</div>
												<div class="text-xs text-accent/70 mt-1">
													{trail.provider || 'External'}
												</div>
											</div>
										</div>

										{#if trail.link}
											<a
												href={trail.link}
												target="_blank"
												rel="noopener noreferrer"
												class="text-xs text-accent hover:text-accent-focus mb-3 break-all block underline"
											>
												{trail.link}
											</a>
										{:else if trail.wanderer_id}
											<div class="text-xs text-base-content/60 mb-3 break-all">
												Wanderer ID: {trail.wanderer_id}
											</div>
										{:else}
											<div class="text-xs text-base-content/40 mb-3 italic">
												No external link available
											</div>
										{/if}

										<!-- Trail Controls -->
										<div class="flex gap-2 justify-end">
											<button
												type="button"
												class="btn btn-warning btn-xs btn-square tooltip tooltip-top"
												data-tip="Edit Trail"
												on:click={() => startEditingTrail(trail)}
											>
												<EditIcon class="w-3 h-3" />
											</button>
											<button
												type="button"
												class="btn btn-error btn-xs btn-square tooltip tooltip-top"
												data-tip="Remove Trail"
												on:click={() => removeTrail(trail.id)}
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
						<div class="text-base-content/60 mb-2">No trails added yet</div>
						<div class="text-sm text-base-content/40">
							Add your first trail using the button above
						</div>
					</div>
				{/if}
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
