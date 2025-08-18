<script lang="ts">
	import type { Checklist, Lodging, Note, Transportation } from '$lib/types';
	import { deserialize } from '$app/forms';
	import { t } from 'svelte-i18n';
	import { addToast } from '$lib/toasts';

	export let object: Lodging | Transportation;
	export let objectType: 'lodging' | 'transportation' | 'note' | 'checklist';
	export let isImagesUploading: boolean = false;

	let imageInput: HTMLInputElement;
	let imageFiles: File[] = [];

	function handleImageChange(event: Event) {
		const target = event.target as HTMLInputElement;
		if (target?.files) {
			imageFiles = Array.from(target.files);
			console.log('Images selected:', imageFiles.length);

			if (object.id) {
				// If object exists, upload immediately
				uploadImages();
			}
		}
	}

	// Watch for external trigger to upload images
	$: {
		if (isImagesUploading && imageFiles.length > 0 && object.id) {
			// Immediately clear the trigger to prevent infinite loop
			const filesToUpload = [...imageFiles];
			imageFiles = []; // Clear immediately
			if (imageInput) {
				imageInput.value = '';
			}
			uploadImagesFromList(filesToUpload);
		}
	}

	async function uploadImages() {
		if (imageFiles.length === 0) {
			isImagesUploading = false;
			return;
		}

		const filesToUpload = [...imageFiles];
		// Clear immediately to prevent re-triggering
		imageFiles = [];
		if (imageInput) {
			imageInput.value = '';
		}

		await uploadImagesFromList(filesToUpload);
	}

	async function uploadImagesFromList(files: File[]) {
		if (files.length === 0) {
			isImagesUploading = false;
			return;
		}

		console.log('Starting image upload for', files.length, 'files');

		try {
			// Upload all images concurrently
			const uploadPromises = files.map((file) => uploadImage(file));
			await Promise.all(uploadPromises);
		} catch (error) {
			console.error('Error uploading images:', error);
			addToast('error', $t('adventures.image_upload_error'));
		} finally {
			isImagesUploading = false;
		}
	}

	async function uploadImage(file: File): Promise<void> {
		let formData = new FormData();
		formData.append('image', file);
		formData.append('object_id', object.id);
		formData.append('content_type', objectType);

		let res = await fetch(`/locations?/image`, {
			method: 'POST',
			body: formData
		});

		if (res.ok) {
			let newData = deserialize(await res.text()) as { data: { id: string; image: string } };
			let newImage = {
				id: newData.data.id,
				image: newData.data.image,
				is_primary: false,
				immich_id: null
			};
			object.images = [...(object.images || []), newImage];
		} else {
			throw new Error(`Failed to upload ${file.name}`);
		}
	}

	async function removeImage(id: string) {
		let res = await fetch(`/api/images/${id}/image_delete`, {
			method: 'POST'
		});
		if (res.status === 204) {
			object.images = object.images.filter((image: { id: string }) => image.id !== id);
			addToast('success', $t('adventures.image_removed_success'));
		} else {
			addToast('error', $t('adventures.image_removed_error'));
		}
	}

	async function makePrimaryImage(image_id: string) {
		let res = await fetch(`/api/images/${image_id}/toggle_primary`, {
			method: 'POST'
		});
		if (res.ok) {
			object.images = object.images.map((image) => {
				if (image.id === image_id) {
					return { ...image, is_primary: true };
				} else {
					return { ...image, is_primary: false };
				}
			});
		} else {
			console.error('Error in makePrimaryImage:', res);
		}
	}

	// Export function to check if images are ready to upload
	export function hasImagesToUpload(): boolean {
		return imageFiles.length > 0;
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
						d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
					/>
				</svg>
			</div>
			{$t('adventures.images')}
			{#if isImagesUploading}
				<span class="loading loading-spinner loading-sm text-primary"></span>
			{/if}
		</div>
	</div>
	<div class="collapse-content bg-base-100/50 pt-4 p-6">
		<div class="form-control">
			<label class="label" for="image">
				<span class="label-text font-medium">{$t('adventures.upload_image')}</span>
			</label>
			<input
				type="file"
				id="image"
				name="image"
				accept="image/*"
				multiple
				bind:this={imageInput}
				on:change={handleImageChange}
				class="file-input file-input-bordered file-input-primary w-full bg-base-100/80 focus:bg-base-100"
				disabled={isImagesUploading}
			/>
		</div>

		{#if imageFiles.length > 0 && !object.id}
			<div class="mt-4">
				<h4 class="font-semibold text-base-content mb-2">
					{$t('adventures.selected_images')} ({imageFiles.length})
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
					<span>{$t('adventures.image_upload_info')} {objectType}</span>
				</div>
				<ul class="list-disc pl-5 space-y-1 mt-2">
					{#each imageFiles as file}
						<li>{file.name} ({Math.round(file.size / 1024)} KB)</li>
					{/each}
				</ul>
			</div>
		{/if}

		{#if object.id}
			<div class="divider my-6"></div>

			<!-- Current Images -->
			<div class="space-y-4">
				<h4 class="font-semibold text-lg">{$t('adventures.my_images')}</h4>

				{#if object.images && object.images.length > 0}
					<div class="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
						{#each object.images as image}
							<div class="relative group">
								<div class="aspect-square overflow-hidden rounded-lg bg-base-300">
									<img
										src={image.image}
										alt={image.id}
										class="w-full h-full object-cover transition-transform group-hover:scale-105"
									/>
								</div>

								<!-- Image Controls -->
								<div
									class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity rounded-lg flex items-center justify-center gap-2"
								>
									{#if !image.is_primary}
										<button
											type="button"
											class="btn btn-success btn-sm"
											on:click={() => makePrimaryImage(image.id)}
											title="Make Primary"
										>
											<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
												></path>
											</svg>
										</button>
									{/if}

									<button
										type="button"
										class="btn btn-error btn-sm"
										on:click={() => removeImage(image.id)}
										title="Remove"
									>
										✕
									</button>
								</div>

								<!-- Primary Badge -->
								{#if image.is_primary}
									<div
										class="absolute top-2 left-2 bg-warning text-warning-content rounded-full p-1"
									>
										<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M5 3l14 9-14 9V3z"
											></path>
										</svg>
									</div>
								{/if}
							</div>
						{/each}
					</div>
				{:else}
					<div class="text-center py-8">
						<div class="text-base-content/60 text-lg mb-2">
							{$t('adventures.no_images')}
						</div>
						<p class="text-sm text-base-content/40">{$t('adventures.no_images_desc')}</p>
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>
