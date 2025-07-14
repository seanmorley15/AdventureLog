<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import ImmichLogo from '$lib/assets/immich.svg';
	import Upload from '~icons/mdi/upload';
	import type { Location, ImmichAlbum } from '$lib/types';
	import { debounce } from '$lib';

	let immichImages: any[] = [];
	let immichSearchValue: string = '';
	let searchCategory: 'search' | 'date' | 'album' = 'date';
	let immichError: string = '';
	let immichNextURL: string = '';
	let loading = false;

	export let location: Location | null = null;
	export let copyImmichLocally: boolean = false;

	const dispatch = createEventDispatcher();

	let albums: ImmichAlbum[] = [];
	let currentAlbum: string = '';

	let selectedDate: string =
		(location as Location | null)?.visits
			.map((v) => new Date(v.end_date || v.start_date))
			.sort((a, b) => +b - +a)[0]
			?.toISOString()
			?.split('T')[0] || '';
	if (!selectedDate) {
		selectedDate = new Date().toISOString().split('T')[0];
	}

	$: {
		if (searchCategory === 'album' && currentAlbum) {
			immichImages = [];
			fetchAlbumAssets(currentAlbum);
		} else if (searchCategory === 'date' && selectedDate) {
			// Clear album selection when switching to date mode
			if (currentAlbum) {
				currentAlbum = '';
			}
			searchImmich();
		} else if (searchCategory === 'search') {
			// Clear album selection when switching to search mode
			if (currentAlbum) {
				currentAlbum = '';
			}
			// Search will be triggered by the form submission or debounced search
		}
	}

	async function loadMoreImmich() {
		// The next URL returned by our API is a absolute url to API, but we need to use the relative path, to use the frontend api proxy.
		const url = new URL(immichNextURL);
		immichNextURL = url.pathname + url.search;
		return fetchAssets(immichNextURL, true);
	}

	async function saveImmichRemoteUrl(imageId: string) {
		if (!location) {
			console.error('No location provided to save the image URL');
			return;
		}
		let res = await fetch('/api/images', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				immich_id: imageId,
				object_id: location.id,
				content_type: 'location'
			})
		});
		if (res.ok) {
			let data = await res.json();
			if (!data.image) {
				console.error('No image data returned from the server');
				immichError = $t('immich.error_saving_image');
				return;
			}
			dispatch('remoteImmichSaved', data);
		} else {
			let errorData = await res.json();
			console.error('Error saving image URL:', errorData);
			immichError = $t(errorData.message || 'immich.error_saving_image');
		}
	}

	async function fetchAssets(url: string, usingNext = false) {
		loading = true;
		try {
			let res = await fetch(url);
			immichError = '';
			if (!res.ok) {
				let data = await res.json();
				let errorMessage = data.message;
				console.error('Error in handling fetchAsstes', errorMessage);
				immichError = $t(data.code);
			} else {
				let data = await res.json();
				if (data.results && data.results.length > 0) {
					if (usingNext) {
						immichImages = [...immichImages, ...data.results];
					} else {
						immichImages = data.results;
					}
				} else {
					immichError = $t('immich.no_items_found');
				}

				immichNextURL = data.next || '';
			}
		} finally {
			loading = false;
		}
	}

	async function fetchAlbumAssets(album_id: string) {
		return fetchAssets(`/api/integrations/immich/albums/${album_id}`);
	}

	onMount(async () => {
		let res = await fetch('/api/integrations/immich/albums');
		if (res.ok) {
			let data = await res.json();
			albums = data;
		}
	});

	function buildQueryParams() {
		let params = new URLSearchParams();
		if (immichSearchValue && searchCategory === 'search') {
			params.append('query', immichSearchValue);
		} else if (selectedDate && searchCategory === 'date') {
			params.append('date', selectedDate);
		}
		return params.toString();
	}

	const searchImmich = debounce(() => {
		_searchImmich();
	}, 500); // Debounce the search function to avoid multiple requests on every key press

	async function _searchImmich() {
		immichImages = [];
		return fetchAssets(`/api/integrations/immich/search/?${buildQueryParams()}`);
	}
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
			on:click={() => {
				searchCategory = 'search';
				currentAlbum = '';
			}}
		>
			{$t('immich.search')}
		</button>
		<button
			class="tab"
			class:tab-active={searchCategory === 'date'}
			on:click={() => (searchCategory = 'date')}
		>
			{$t('immich.by_date')}
		</button>
		<button
			class="tab"
			class:tab-active={searchCategory === 'album'}
			on:click={() => (searchCategory = 'album')}
		>
			{$t('immich.by_album')}
		</button>
	</div>

	<!-- Search Controls -->
	<div class="bg-base-100 p-4 rounded-lg border border-base-300">
		{#if searchCategory === 'search'}
			<form on:submit|preventDefault={searchImmich} class="flex gap-2">
				<input
					type="text"
					placeholder={$t('immich.search_placeholder')}
					bind:value={immichSearchValue}
					class="input input-bordered flex-1"
				/>
				<button type="submit" class="btn btn-primary">
					{$t('immich.search')}
				</button>
			</form>
		{:else if searchCategory === 'date'}
			<div class="flex items-center gap-2">
				<label class="label">
					<span class="label-text">{$t('immich.select_date')}</span>
				</label>
				<input type="date" bind:value={selectedDate} class="input input-bordered w-full max-w-xs" />
			</div>
		{:else if searchCategory === 'album'}
			<div class="flex items-center gap-2">
				<label class="label">
					<span class="label-text">{$t('immich.select_album')}</span>
				</label>
				<select class="select select-bordered w-full max-w-xs" bind:value={currentAlbum}>
					<option value="" disabled selected>{$t('immich.select_album_placeholder')}</option>
					{#each albums as album}
						<option value={album.id}>{album.albumName}</option>
					{/each}
				</select>
			</div>
		{/if}
	</div>

	<!-- Error Message -->
	{#if immichError}
		<div class="alert alert-error">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="stroke-current shrink-0 h-6 w-6"
				fill="none"
				viewBox="0 0 24 24"
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
				<span class="loading loading-spinner loading-lg"></span>
			</div>
		{/if}

		<!-- Images Grid -->
		<div class="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4" class:opacity-50={loading}>
			{#each immichImages as image}
				<div class="card bg-base-100 shadow-sm hover:shadow-md transition-shadow">
					<figure class="aspect-square">
						<img src={image.image_url} alt="Image from Immich" class="w-full h-full object-cover" />
					</figure>
					<div class="card-body p-2">
						<button
							type="button"
							class="btn btn-primary btn-sm max-w-full"
							on:click={() => {
								let currentDomain = window.location.origin;
								let fullUrl = `${currentDomain}/immich/${image.id}`;
								if (copyImmichLocally) {
									dispatch('fetchImage', fullUrl);
								} else {
									saveImmichRemoteUrl(image.id);
								}
							}}
						>
							<Upload class="w-4 h-4" />
						</button>
					</div>
				</div>
			{/each}
		</div>

		<!-- Load More Button -->
		{#if immichNextURL}
			<div class="flex justify-center mt-6">
				<button class="btn btn-outline btn-wide" on:click={loadMoreImmich}>
					{$t('immich.load_more')}
				</button>
			</div>
		{/if}
	</div>
</div>
