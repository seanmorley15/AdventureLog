<script lang="ts">
	import { run } from 'svelte/legacy';

	import { createEventDispatcher, onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import CheckIcon from '~icons/mdi/check';
	import CloseIcon from '~icons/mdi/close';
	import type { ImmichAlbum } from '$lib/types';
	import { debounce } from '$lib';

	
	interface Props {
		// Props
		copyImmichLocally?: boolean;
		objectId?: string;
		contentType?: string;
		defaultDate?: string;
	}

	let {
		copyImmichLocally = false,
		objectId = '',
		contentType = 'location',
		defaultDate = ''
	}: Props = $props();

	// Component state
	let immichImages: any[] = $state([]);
	let immichSearchValue: string = $state('');
	let searchCategory: 'search' | 'date' | 'album' = $state('date');
	let immichError: string = $state('');
	let immichNextURL: string = $state('');
	let loading = $state(false);
	let albums: ImmichAlbum[] = $state([]);
	let currentAlbum: string = $state('');
	let selectedDate: string = $state(new Date().toISOString().split('T')[0]);

	$effect.pre(() => {
		if (defaultDate) {
			selectedDate = defaultDate;
		}
	});

	const dispatch = createEventDispatcher<{
		localImage: { file: File; immichId: string };
		remoteImmichSaved: Record<string, unknown>;
	}>();


	// Helper functions
	function clearAlbumSelection() {
		if (currentAlbum) {
			currentAlbum = '';
		}
	}

	function buildQueryParams(): string {
		const params = new URLSearchParams();

		if (immichSearchValue && searchCategory === 'search') {
			params.append('query', immichSearchValue);
		} else if (selectedDate && searchCategory === 'date') {
			params.append('date', selectedDate);
		}

		return params.toString();
	}

	// API functions
	async function fetchAssets(url: string, usingNext = false): Promise<void> {
		loading = true;
		immichError = '';

		try {
			const res = await fetch(url);

			if (!res.ok) {
				const data = await res.json();
				console.error('Error in fetchAssets:', data.message);
				immichError = $t(data.code || 'immich.fetch_error');
				return;
			}

			const data = await res.json();

			if (data.results && data.results.length > 0) {
				if (usingNext) {
					immichImages = [...immichImages, ...data.results];
				} else {
					immichImages = data.results;
				}
				immichNextURL = data.next || '';
			} else {
				immichError = $t('immich.no_items_found');
				immichNextURL = '';
			}
		} catch (error) {
			console.error('Error fetching assets:', error);
			immichError = $t('immich.fetch_error');
		} finally {
			loading = false;
		}
	}

	async function fetchAlbumAssets(albumId: string): Promise<void> {
		return fetchAssets(`/api/integrations/immich/albums/${albumId}`);
	}

	async function loadMoreImmich(): Promise<void> {
		if (!immichNextURL) return;

		// Convert absolute URL to relative path for frontend API proxy
		const url = new URL(immichNextURL);
		const relativePath = url.pathname + url.search;

		return fetchAssets(relativePath, true);
	}

	async function saveImmichRemoteUrl(imageId: string): Promise<void> {
		if (!objectId) {
			console.error('No object ID provided to save the image URL');
			immichError = $t('immich.error_no_object_id');
			return;
		}

		try {
			const res = await fetch('/api/images', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					immich_id: imageId,
					object_id: objectId,
					content_type: contentType
				})
			});

			if (res.ok) {
				const data = await res.json();

				if (!data.image) {
					console.error('No image data returned from the server');
					immichError = $t('immich.error_saving_image');
					return;
				}

				dispatch('remoteImmichSaved', data);
			} else {
				const errorData = await res.json();
				console.error('Error saving image URL:', errorData);
				immichError = $t(errorData.message || 'immich.error_saving_image');
			}
		} catch (error) {
			console.error('Error in saveImmichRemoteUrl:', error);
			immichError = $t('immich.error_saving_image');
		}
	}

	// Event handlers
	const searchImmich = debounce(() => {
		_searchImmich();
	}, 500);

	async function _searchImmich(): Promise<void> {
		immichImages = [];
		return fetchAssets(`/api/integrations/immich/search/?${buildQueryParams()}`);
	}

	function handleSearchCategoryChange(category: 'search' | 'date' | 'album') {
		searchCategory = category;
		immichError = '';

		if (category !== 'album') {
			clearAlbumSelection();
		}
	}

	async function copyImmichImageLocally(image: { id: string }) {
		if (!objectId) {
			immichError = $t('immich.error_no_object_id');
			return;
		}

		loading = true;
		immichError = '';

		try {
			const res = await fetch(`/immich/${image.id}`);
			if (!res.ok) {
				immichError = $t('immich.error_saving_image');
				return;
			}

			const blob = await res.blob();
			const contentType = blob.type && blob.type.startsWith('image/') ? blob.type : 'image/jpeg';
			const extension = contentType.includes('png')
				? 'png'
				: contentType.includes('webp')
					? 'webp'
					: 'jpg';
			const file = new File([blob], `immich_${image.id}.${extension}`, { type: contentType });
			dispatch('localImage', { file, immichId: image.id });
		} catch (error) {
			console.error('Error copying Immich image locally:', error);
			immichError = $t('immich.error_saving_image');
		} finally {
			loading = false;
		}
	}

	function handleImageSelect(image: { id: string }) {
		if (copyImmichLocally) {
			void copyImmichImageLocally(image);
			return;
		}
		saveImmichRemoteUrl(image.id);
	}

	// Lifecycle
	onMount(async () => {
		try {
			const res = await fetch('/api/integrations/immich/albums');

			if (res.ok) {
				const data = await res.json();
				albums = data;
			} else {
				console.warn('Failed to fetch Immich albums');
			}
		} catch (error) {
			console.error('Error fetching albums:', error);
		}
	});
	// Reactive statements
	run(() => {
		if (searchCategory === 'album' && currentAlbum) {
			immichImages = [];
			fetchAlbumAssets(currentAlbum);
		} else if (searchCategory === 'date' && selectedDate) {
			clearAlbumSelection();
			searchImmich();
		} else if (searchCategory === 'search') {
			clearAlbumSelection();
		}
	});
</script>

<!-- Search Category Tabs -->
<div class="flex gap-2 mb-3">
	<button
		class="btn btn-sm"
		class:btn-primary={searchCategory === 'search'}
		class:btn-ghost={searchCategory !== 'search'}
		onclick={() => handleSearchCategoryChange('search')}
	>
		{$t('navbar.search')}
	</button>
	<button
		class="btn btn-sm"
		class:btn-primary={searchCategory === 'date'}
		class:btn-ghost={searchCategory !== 'date'}
		onclick={() => handleSearchCategoryChange('date')}
	>
		{$t('immich.by_date')}
	</button>
	<button
		class="btn btn-sm"
		class:btn-primary={searchCategory === 'album'}
		class:btn-ghost={searchCategory !== 'album'}
		onclick={() => handleSearchCategoryChange('album')}
	>
		{$t('immich.by_album')}
	</button>
</div>

<!-- Search Controls -->
{#if searchCategory === 'search'}
	<div class="flex gap-2">
		<input
			type="text"
			placeholder={$t('immich.image_search_placeholder') + '...'}
			bind:value={immichSearchValue}
			class="input input-bordered flex-1"
			disabled={loading}
		/>
		<button
			type="submit"
			class="btn btn-primary btn-sm"
			class:loading
			disabled={loading || !immichSearchValue.trim()}
			onclick={searchImmich}
		>
			{$t('navbar.search')}
		</button>
	</div>
{:else if searchCategory === 'date'}
	<div class="flex gap-2 items-center">
		<input
			id="date-picker"
			type="date"
			bind:value={selectedDate}
			class="input input-bordered flex-1"
			disabled={loading}
		/>
	</div>
{:else if searchCategory === 'album'}
	<select
		id="album-select"
		class="select select-bordered w-full"
		bind:value={currentAlbum}
		disabled={loading}
	>
		<option value="" disabled>
			{albums.length > 0 ? $t('immich.select_album') : $t('immich.loading_albums')}
		</option>
		{#each albums as album (album.id)}
			<option value={album.id}>{album.albumName}</option>
		{/each}
	</select>
{/if}

<!-- Error Message -->
{#if immichError}
	<div class="alert alert-error mt-2 py-2">
		<span class="text-sm">{immichError}</span>
	</div>
{/if}

<!-- Images Results (Inline) -->
{#if immichImages.length > 0}
	<div class="mt-4">
		<div class="flex items-center justify-between mb-3">
			<span class="text-sm text-base-content/70">
				{immichImages.length}
				{immichImages.length === 1 ? 'image' : 'images'} found
			</span>
			<button
				class="btn btn-ghost btn-xs"
				onclick={() => {
					immichImages = [];
					immichSearchValue = '';
					immichNextURL = '';
				}}
			>
				<CloseIcon class="h-4 w-4" />
			</button>
		</div>
		<div class="grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-96 overflow-y-auto">
			{#each immichImages as image (image.id)}
				<button
					type="button"
					class="card bg-base-100 border border-base-300 hover:border-primary hover:shadow-lg transition-all duration-200 cursor-pointer group relative"
					onclick={() => handleImageSelect(image)}
					disabled={loading}
				>
					<figure class="aspect-square bg-base-200 overflow-hidden">
						<img
							src={image.image_url}
							alt="Immich"
							class="w-full h-full object-cover transition-transform group-hover:scale-105"
							loading="lazy"
						/>
					</figure>
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

		<!-- Load More Button -->
		{#if immichNextURL}
			<div class="flex justify-center mt-3">
				<button
					class="btn btn-outline btn-sm btn-wide"
					onclick={loadMoreImmich}
					disabled={loading}
				>
					{loading ? $t('immich.loading') : $t('immich.load_more')}
				</button>
			</div>
		{/if}
	</div>
{/if}
