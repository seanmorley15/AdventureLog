<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import ImmichLogo from '$lib/assets/immich.svg';
	import Upload from '~icons/mdi/upload';
	import type { ImmichAlbum } from '$lib/types';
	import { debounce } from '$lib';

	// Props
	export let copyImmichLocally: boolean = false;
	export let objectId: string = '';
	export let contentType: string = 'location';
	export let defaultDate: string = '';

	// Component state
	let immichImages: any[] = [];
	let immichSearchValue: string = '';
	let searchCategory: 'search' | 'date' | 'album' = 'date';
	let immichError: string = '';
	let immichNextURL: string = '';
	let loading = false;
	let albums: ImmichAlbum[] = [];
	let currentAlbum: string = '';
	let selectedDate: string = defaultDate || new Date().toISOString().split('T')[0];

	const dispatch = createEventDispatcher();

	// Reactive statements
	$: {
		if (searchCategory === 'album' && currentAlbum) {
			immichImages = [];
			fetchAlbumAssets(currentAlbum);
		} else if (searchCategory === 'date' && selectedDate) {
			clearAlbumSelection();
			searchImmich();
		} else if (searchCategory === 'search') {
			clearAlbumSelection();
		}
	}

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

	function handleImageSelect(image: any) {
		const currentDomain = window.location.origin;
		const fullUrl = `${currentDomain}/immich/${image.id}`;

		if (copyImmichLocally) {
			dispatch('fetchImage', fullUrl);
		} else {
			saveImmichRemoteUrl(image.id);
		}
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
</script>

<div class="space-y-4">
	<!-- Header -->
	<div class="flex items-center gap-2 mb-4">
		<h4 class="font-medium text-lg">
			{$t('immich.immich')}
		</h4>
		<img src={ImmichLogo} alt="Immich Logo" class="h-6 w-6" />
	</div>

	<!-- Search Category Tabs -->
	<div class="tabs tabs-boxed w-fit">
		<button
			class="tab"
			class:tab-active={searchCategory === 'search'}
			on:click={() => handleSearchCategoryChange('search')}
		>
			{$t('navbar.search')}
		</button>
		<button
			class="tab"
			class:tab-active={searchCategory === 'date'}
			on:click={() => handleSearchCategoryChange('date')}
		>
			{$t('immich.by_date')}
		</button>
		<button
			class="tab"
			class:tab-active={searchCategory === 'album'}
			on:click={() => handleSearchCategoryChange('album')}
		>
			{$t('immich.by_album')}
		</button>
	</div>

	<!-- Search Controls -->
	<div class="bg-base-50 p-4 rounded-lg border border-base-200">
		{#if searchCategory === 'search'}
			<form on:submit|preventDefault={searchImmich} class="flex gap-2">
				<input
					type="text"
					placeholder={$t('immich.image_search_placeholder') + '...'}
					bind:value={immichSearchValue}
					class="input input-bordered flex-1"
					disabled={loading}
				/>
				<button
					type="submit"
					class="btn btn-primary"
					class:loading
					disabled={loading || !immichSearchValue.trim()}
				>
					{$t('navbar.search')}
				</button>
			</form>
		{:else if searchCategory === 'date'}
			<div class="flex items-center gap-2">
				<label class="label" for="date-picker">
					<span class="label-text">{$t('immich.select_date')}</span>
				</label>
				<input
					id="date-picker"
					type="date"
					bind:value={selectedDate}
					class="input input-bordered w-full max-w-xs"
					disabled={loading}
				/>
			</div>
		{:else if searchCategory === 'album'}
			<div class="flex items-center gap-2">
				<label class="label" for="album-select">
					<span class="label-text">{$t('immich.select_album')}</span>
				</label>
				<select
					id="album-select"
					class="select select-bordered w-full max-w-xs"
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
			</div>
		{/if}
	</div>

	<!-- Error Message -->
	{#if immichError}
		<div class="alert alert-error py-2">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="stroke-current shrink-0 h-5 w-5"
				fill="none"
				viewBox="0 0 24 24"
				aria-hidden="true"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
				/>
			</svg>
			<span class="text-sm">{immichError}</span>
		</div>
	{/if}

	<!-- Images Grid -->
	<div class="relative">
		<!-- Loading Overlay -->
		{#if loading}
			<div
				class="absolute inset-0 bg-base-200/50 backdrop-blur-sm z-10 flex items-center justify-center rounded-lg"
			>
				<div class="flex flex-col items-center gap-2">
					<span class="loading loading-spinner loading-lg"></span>
					<span class="text-sm text-base-content/70">{$t('immich.loading')}</span>
				</div>
			</div>
		{/if}

		<!-- Images Grid -->
		{#if immichImages.length > 0}
			<div
				class="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4"
				class:opacity-50={loading}
			>
				{#each immichImages as image (image.id)}
					<div
						class="card bg-base-100 shadow-sm hover:shadow-md transition-all duration-200 border border-base-200"
					>
						<figure class="aspect-square overflow-hidden">
							<img
								src={image.image_url}
								alt="Image from Immich"
								class="w-full h-full object-cover hover:scale-105 transition-transform duration-200"
								loading="lazy"
							/>
						</figure>
						<div class="card-body p-3">
							<button
								type="button"
								class="btn btn-primary btn-sm w-full gap-2"
								disabled={loading}
								on:click={() => handleImageSelect(image)}
							>
								<Upload class="w-4 h-4" />
							</button>
						</div>
					</div>
				{/each}
			</div>
		{:else if !loading && searchCategory !== 'search'}
			<div class="bg-base-200/50 rounded-lg p-8 text-center">
				<div class="text-base-content/60 mb-2">{$t('immich.no_images')}</div>
				<div class="text-sm text-base-content/40">
					{#if searchCategory === 'date'}
						{$t('immich.try_different_date')}
					{:else if searchCategory === 'album'}
						{$t('immich.select_album_first')}
					{/if}
				</div>
			</div>
		{/if}

		<!-- Load More Button -->
		{#if immichNextURL && !loading}
			<div class="flex justify-center mt-6">
				<button class="btn btn-outline btn-wide" on:click={loadMoreImmich} disabled={loading}>
					{$t('immich.load_more')}
				</button>
			</div>
		{/if}
	</div>
</div>
