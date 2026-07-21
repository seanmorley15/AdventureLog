<script lang="ts">
	import type { ContentImage, ImageSource } from '$lib/types';
	import { normalizeContentImage } from '$lib/images';
	import { createEventDispatcher, onMount } from 'svelte';
	import { t, locale } from 'svelte-i18n';
	import { deserialize } from '$app/forms';

	// Icons
	import Star from '~icons/mdi/star';
	import Crown from '~icons/mdi/crown';
	import TrashIcon from '~icons/mdi/delete';
	import CheckIcon from '~icons/mdi/check';
	import CloseIcon from '~icons/mdi/close';
	import ImageIcon from '~icons/mdi/image';
	import GoogleIcon from '~icons/mdi/google';

	import { addToast } from '$lib/toasts';
	import ImmichSelect from './ImmichSelect.svelte';
	import ImageFrame from './ImageFrame.svelte';

	// Props
	export let images: ContentImage[] = [];
	export let objectId: string = '';
	export let contentType: string = 'location'; // 'location', 'adventure', 'collection', etc.
	export let defaultSearchTerm: string = '';
	export let immichIntegration: boolean = false;
	export let copyImmichLocally: boolean = false;
	/** Google photo URLs from place search; imported only when the user chooses. */
	export let pendingGooglePhotoUrls: string[] = [];

	// Component state
	let fileInput: HTMLInputElement;
	let url: string = '';
	let imageSearch: string = defaultSearchTerm;
	let imageError: string = '';
	let wikiImageError: string = '';
	let isLoading: boolean = false;
	let importingGooglePhotos = false;
	let googlePhotoError = '';
	let deselectedGooglePhotoUrls = new Set<string>();

	$: selectedGooglePhotoUrls = pendingGooglePhotoUrls.filter(
		(url) => !deselectedGooglePhotoUrls.has(url)
	);

	$: if (pendingGooglePhotoUrls.length === 0) {
		deselectedGooglePhotoUrls = new Set();
	}

	// Wikipedia image selection
	let wikiImageResults: Array<{
		source: string;
		width: number;
		height: number;
		title: string;
		type: string;
	}> = [];

	const dispatch = createEventDispatcher<{
		imagesUpdated: ContentImage[];
	}>();

	// Helper functions
	function createImageFromData(
		data: Partial<ContentImage> & Pick<ContentImage, 'id' | 'image'>
	): ContentImage {
		return normalizeContentImage({
			...data,
			is_primary: data.is_primary ?? false
		});
	}

	function updateImagesList(newImage: ContentImage) {
		images = [...images, newImage];
		dispatch('imagesUpdated', images);
	}

	// API calls
	async function uploadImageToServer(
		file: File,
		options: { source?: ImageSource; sourceUrl?: string; immichId?: string } = {}
	) {
		if (!objectId) {
			console.error('Cannot upload image: objectId is not set');
			addToast('error', 'Cannot upload image: location must be saved first');
			return null;
		}

		const formData = new FormData();
		formData.append('image', file);
		formData.append('object_id', objectId);
		formData.append('content_type', contentType);
		if (options.source) {
			formData.append('source', options.source);
		}
		if (options.sourceUrl) {
			formData.append('source_url', options.sourceUrl);
		}
		if (options.immichId) {
			formData.append('immich_id', options.immichId);
		}

		try {
			const res = await fetch(`/locations?/image`, {
				method: 'POST',
				credentials: 'same-origin',
				body: formData
			});

			if (res.ok) {
				const newData = deserialize(await res.text()) as {
					data: Partial<ContentImage> & { id: string; image: string; error?: string };
				};
				// Check if the server action returned an error
				if (newData.data && newData.data.error) {
					console.error('Image upload server error:', newData.data.error);
					addToast('error', String(newData.data.error));
					return null;
				}
				if (!newData.data || !newData.data.id || !newData.data.image) {
					console.error('Image upload returned incomplete data:', newData.data);
					addToast('error', 'Image upload failed - incomplete response');
					return null;
				}
				return createImageFromData(newData.data);
			} else {
				throw new Error('Upload failed');
			}
		} catch (error) {
			console.error('Upload error:', error);
			return null;
		}
	}

	// Import temporary recommendation images (id starting with 'rec-') once objectId is available
	export let importInProgress: boolean = false;

	async function importPrefilledImagesIfNeeded() {
		if (importInProgress) return;
		if (!objectId || !images || images.length === 0) return;
		const prefilled = images.filter((img) => img.id && img.id.startsWith('rec-'));
		if (prefilled.length === 0) return;

		importInProgress = true;
		for (const img of prefilled) {
			try {
				const res = await fetch(img.image);
				if (!res.ok) throw new Error('Failed to fetch image');
				const blob = await res.blob();
				const file = new File([blob], 'image.jpg', { type: blob.type || 'image/jpeg' });

				const newImage = await uploadImageToServer(file, { source: 'google' });
				if (newImage) {
					images = images.map((i) => (i.id === img.id ? newImage : i));
					dispatch('imagesUpdated', images);
					addToast('success', $t('adventures.image_upload_success'));
				} else {
					throw new Error('Upload failed');
				}
			} catch (err) {
				console.error('Error importing prefilled image:', err);
				addToast('error', $t('adventures.image_upload_error'));
			}
		}
		importInProgress = false;
	}

	onMount(() => {
		importPrefilledImagesIfNeeded();
	});

	// React to objectId becoming available later
	$: if (objectId) {
		importPrefilledImagesIfNeeded();
	}

	async function fetchImageFromUrl(imageUrl: string): Promise<Blob | null> {
		try {
			// Use backend proxy to avoid CORS issues with external URLs (Wikipedia, etc.)
			const res = await fetch('/api/images/fetch_from_url/', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ url: imageUrl })
			});
			if (!res.ok) {
				let errorMsg = 'Failed to fetch image';
				try {
					const errorData = await res.json();
					errorMsg = errorData.error || errorMsg;
				} catch {
					// Response wasn't JSON (e.g. timeout), use default message
				}
				throw new Error(errorMsg);
			}
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
			const newImage = await uploadImageToServer(file, { source: 'url', sourceUrl: url.trim() });

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
			const res = await fetch(
				`/api/generate/img/?name=${encodeURIComponent(imageSearch)}&lang=${$locale || 'en'}`
			);
			const data = await res.json();

			if (!res.ok || !data.images || data.images.length === 0) {
				wikiImageError = $t('adventures.image_fetch_failed');
				return;
			}

			// Store results to display inline (deduplicated by source)
			{
				const seen = new Set();
				wikiImageResults = (data.images || []).filter((img: { source: unknown }) => {
					if (!img || !img.source) return false;
					if (seen.has(img.source)) return false;
					seen.add(img.source);
					return true;
				});
			}
		} catch (error) {
			wikiImageError = $t('adventures.wiki_image_error');
			addToast('error', $t('adventures.image_upload_error'));
		} finally {
			isLoading = false;
		}
	}

	async function selectWikiImage(imageUrl: string) {
		isLoading = true;

		try {
			const blob = await fetchImageFromUrl(imageUrl);
			if (!blob) {
				wikiImageError = $t('adventures.image_fetch_failed');
				isLoading = false;
				return;
			}

			const file = new File([blob], `${imageSearch}.jpg`, { type: 'image/jpeg' });
			const newImage = await uploadImageToServer(file, {
				source: 'wikipedia',
				sourceUrl: imageUrl
			});

			if (newImage) {
				updateImagesList(newImage);
				addToast('success', $t('adventures.image_upload_success'));
				// Keep results open to allow adding multiple images
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
				dispatch('imagesUpdated', images);
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
				dispatch('imagesUpdated', images);
				addToast('success', 'Image removed');
			} else {
				throw new Error('Failed to remove image');
			}
		} catch (error) {
			console.error('Error removing image:', error);
			addToast('error', 'Failed to remove image');
		}
	}

	function handleImmichImageSaved(event: CustomEvent) {
		const newImage = createImageFromData(event.detail);
		updateImagesList(newImage);
		addToast('success', $t('adventures.image_upload_success'));
	}

	async function handleImmichLocalImage(event: CustomEvent<{ file: File; immichId: string }>) {
		if (!objectId) {
			addToast('error', $t('adventures.image_upload_error'));
			return;
		}

		isLoading = true;
		imageError = '';

		try {
			const newImage = await uploadImageToServer(event.detail.file, {
				source: 'immich',
				immichId: event.detail.immichId
			});
			if (newImage) {
				updateImagesList(newImage);
				addToast('success', $t('adventures.image_upload_success'));
			} else {
				throw new Error('Upload failed');
			}
		} catch (error) {
			console.error('Immich local upload error:', error);
			imageError = $t('adventures.image_fetch_failed');
			addToast('error', $t('adventures.image_upload_error'));
		} finally {
			isLoading = false;
		}
	}

	// Watch for defaultSearchTerm changes
	$: if (defaultSearchTerm && !imageSearch) {
		imageSearch = defaultSearchTerm;
	}

	function toggleGooglePhotoSelection(url: string) {
		if (deselectedGooglePhotoUrls.has(url)) {
			deselectedGooglePhotoUrls.delete(url);
		} else {
			deselectedGooglePhotoUrls.add(url);
		}
		deselectedGooglePhotoUrls = deselectedGooglePhotoUrls;
	}

	async function importGooglePhotos(urls: string[]) {
		if (!objectId || urls.length === 0) return;

		importingGooglePhotos = true;
		importInProgress = true;
		googlePhotoError = '';

		try {
			const res = await fetch('/api/images/import_from_urls/', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					content_type: contentType,
					object_id: objectId,
					urls,
					source: 'google'
				})
			});

			if (!res.ok) {
				googlePhotoError = $t('adventures.google_photos_import_error');
				addToast('warning', $t('adventures.google_photos_import_error'));
				return;
			}

			const data = await res.json();
			if (Array.isArray(data.created) && data.created.length > 0) {
				const existingIds = new Set(images.map((img) => img.id));
				const imported = data.created
					.filter((img: ContentImage) => !existingIds.has(img.id))
					.map((img: ContentImage) => createImageFromData(img));
				images = [...images, ...imported];
				dispatch('imagesUpdated', images);
				addToast('success', $t('adventures.google_photos_import_success'));
			}

			const importedUrls = new Set(urls);
			pendingGooglePhotoUrls = pendingGooglePhotoUrls.filter((url) => !importedUrls.has(url));
		} catch {
			googlePhotoError = $t('adventures.google_photos_import_error');
			addToast('warning', $t('adventures.google_photos_import_error'));
		} finally {
			importingGooglePhotos = false;
			importInProgress = false;
		}
	}

	function importAllGooglePhotos() {
		void importGooglePhotos([...pendingGooglePhotoUrls]);
	}

	function importSelectedGooglePhotos() {
		void importGooglePhotos([...selectedGooglePhotoUrls]);
	}
</script>

<div class="card bg-base-100 border border-base-300 shadow-lg">
	<div class="card-body p-6">
		<div class="flex items-center gap-3 mb-6">
			<div class="p-2 bg-primary/10 rounded-lg">
				<ImageIcon class="w-5 h-5 text-primary" />
			</div>
			<h2 class="text-xl font-bold">{$t('adventures.image_management')}</h2>
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
						{$t('navbar.search')}
					</button>
				</div>
				{#if wikiImageError}
					<div class="alert alert-error mt-2 py-2">
						<span class="text-sm">{wikiImageError}</span>
					</div>
				{/if}

				<!-- Wikipedia Image Results (Inside Box) -->
				{#if wikiImageResults.length > 0}
					<div class="mt-4">
						<div class="flex items-center justify-between mb-3">
							<span class="text-sm text-base-content/70">
								{$t('adventures.wiki_results_found', {
									values: { count: wikiImageResults.length, query: imageSearch }
								})}
							</span>
							<button
								class="btn btn-ghost btn-xs"
								on:click={() => {
									wikiImageResults = [];
									imageSearch = defaultSearchTerm;
								}}
							>
								<CloseIcon class="h-4 w-4" />
							</button>
						</div>
						<div class="grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-96 overflow-y-auto">
							{#each wikiImageResults as result, i (result.source + '-' + i)}
								<button
									type="button"
									class="card bg-base-100 border border-base-300 hover:border-primary hover:shadow-lg transition-all duration-200 cursor-pointer group"
									on:click={() => selectWikiImage(result.source)}
									disabled={isLoading}
								>
									<figure class="aspect-square bg-base-200 overflow-hidden">
										<img
											src={result.source}
											alt={result.title}
											class="w-full h-full object-cover transition-transform group-hover:scale-105"
											loading="lazy"
										/>
									</figure>
									<div class="card-body p-2">
										<h4 class="text-xs font-medium line-clamp-1 text-left" title={result.title}>
											{result.title}
										</h4>
										<div
											class="text-xs text-base-content/60 flex items-center justify-between gap-1"
										>
											<span class="truncate">{result.width} × {result.height}</span>
										</div>
									</div>
									<div
										class="absolute inset-0 bg-primary/10 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center justify-center rounded-2xl"
									>
										<div class="btn btn-primary btn-sm gap-2">
											<CheckIcon class="h-4 w-4" />
											{$t('adventures.select')}
										</div>
									</div>
								</button>
							{/each}
						</div>
					</div>
				{/if}
			</div>

			<!-- Immich Integration -->
			{#if immichIntegration}
				<div class="bg-base-50 p-4 rounded-lg border border-base-200">
					<h4 class="font-medium mb-3 text-base-content/80">
						{$t('immich.immich')}
					</h4>
					<ImmichSelect
						{objectId}
						{contentType}
						{copyImmichLocally}
						on:localImage={handleImmichLocalImage}
						on:remoteImmichSaved={handleImmichImageSaved}
					/>
				</div>
			{/if}
		</div>

		{#if pendingGooglePhotoUrls.length > 0}
			<div class="bg-base-50 p-4 rounded-lg border border-base-200 mb-6 relative">
				<div class="flex items-center gap-3 mb-3">
					<div class="p-2 bg-primary/10 rounded-lg">
						<GoogleIcon class="w-5 h-5 text-primary" />
					</div>
					<div class="flex-1">
						<h4 class="font-medium text-base-content/80">
							{$t('adventures.google_photos_available', {
								values: { count: pendingGooglePhotoUrls.length }
							})}
						</h4>
						<p class="text-sm text-base-content/60">
							{$t('adventures.google_photos_select_hint')}
						</p>
					</div>
				</div>

				<div class="relative mb-4">
					<div
						class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2 transition-opacity duration-200 {importingGooglePhotos
							? 'opacity-40 pointer-events-none'
							: ''}"
					>
						{#each pendingGooglePhotoUrls as url, i (url + '-' + i)}
							<button
								type="button"
								class="relative aspect-square overflow-hidden rounded-lg border-2 transition-all cursor-pointer group {!deselectedGooglePhotoUrls.has(
									url
								)
									? 'border-primary ring-2 ring-primary/30'
									: 'border-base-300 opacity-70 hover:opacity-100'}"
								on:click={() => toggleGooglePhotoSelection(url)}
								disabled={importingGooglePhotos || !objectId}
							>
								<img
									src={url}
									alt="Google place photo"
									class="w-full h-full object-cover"
									loading="lazy"
								/>
								{#if !deselectedGooglePhotoUrls.has(url)}
									<div
										class="absolute top-1 right-1 bg-primary text-primary-content rounded-full p-0.5"
									>
										<CheckIcon class="h-3 w-3" />
									</div>
								{/if}
							</button>
						{/each}
					</div>

					{#if importingGooglePhotos}
						<div
							class="absolute inset-0 flex flex-col items-center justify-center gap-3 rounded-lg bg-base-100/60 backdrop-blur-[2px]"
							role="status"
							aria-live="polite"
						>
							<span class="loading loading-spinner loading-md text-primary"></span>
							<span class="text-sm font-medium text-base-content/80">
								{$t('adventures.google_photos_importing')}
							</span>
						</div>
					{/if}
				</div>

				<div class="flex flex-wrap gap-2">
					<button
						type="button"
						class="btn btn-primary btn-sm"
						disabled={importingGooglePhotos || !objectId || pendingGooglePhotoUrls.length === 0}
						on:click={importAllGooglePhotos}
					>
						{$t('adventures.google_photos_import_all')}
					</button>
					<button
						type="button"
						class="btn btn-outline btn-sm"
						disabled={importingGooglePhotos || !objectId || selectedGooglePhotoUrls.length === 0}
						on:click={importSelectedGooglePhotos}
					>
						{$t('adventures.google_photos_import_selected')}
					</button>
				</div>

				{#if !objectId}
					<p class="text-sm text-warning mt-2">Save the item first to import Google photos.</p>
				{/if}

				{#if googlePhotoError}
					<div class="alert alert-error mt-2 py-2">
						<span class="text-sm">{googlePhotoError}</span>
					</div>
				{/if}
			</div>
		{/if}

		<!-- Image Gallery -->
		{#if images.length > 0}
			<div class="divider">Current Images</div>
			<div class="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
				{#each images as image, i (image.id ?? image.image ?? `img-${i}`)}
					<div class="relative group">
						<ImageFrame
							source={image.source}
							showSourceBadge
							className="aspect-square overflow-hidden rounded-lg bg-base-200 border border-base-300"
						>
							<img
								src={image.image}
								alt="Uploaded content"
								class="w-full h-full object-cover transition-transform group-hover:scale-105"
								loading="lazy"
							/>
							<div slot="overlays">
								{#if image.is_primary}
									<div
										class="absolute top-2 left-2 bg-warning text-warning-content rounded-full p-1 shadow-lg"
									>
										<Crown class="h-4 w-4" />
									</div>
								{/if}
							</div>
						</ImageFrame>

						<div
							class="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-all duration-200 rounded-lg flex items-center justify-center gap-2"
						>
							{#if !image.is_primary}
								<button
									type="button"
									class="btn btn-success btn-sm tooltip tooltip-top"
									data-tip="Make Primary"
									on:click={() => image.id && makePrimaryImage(image.id)}
									disabled={!image.id}
								>
									<Star class="h-4 w-4" />
								</button>
							{/if}

							<button
								type="button"
								class="btn btn-error btn-sm tooltip tooltip-top"
								data-tip="Remove Image"
								on:click={() => image.id && removeImage(image.id)}
								disabled={!image.id}
							>
								<TrashIcon class="h-4 w-4" />
							</button>
						</div>
					</div>
				{/each}
			</div>
		{:else}
			<div class="bg-base-200/50 rounded-lg p-8 text-center">
				<div class="text-base-content/60 mb-2">{$t('adventures.no_images_uploaded_yet')}</div>
				<div class="text-sm text-base-content/40">
					{$t('adventures.upload_first_image')}
				</div>
			</div>
		{/if}
	</div>
</div>
