<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import ImmichLogo from '$lib/assets/immich.svg';
	import type { Adventure, ImmichAlbum } from '$lib/types';
	import { debounce } from '$lib';

	let immichImages: any[] = [];
	let immichSearchValue: string = '';
	let searchCategory: 'search' | 'date' | 'album' = 'date';
	let immichError: string = '';
	let immichNextURL: string = '';
	let loading = false;

	export let adventure: Adventure | null = null;
	
	const dispatch = createEventDispatcher();

	let albums: ImmichAlbum[] = [];
	let currentAlbum: string = '';

	let selectedDate: string =  (adventure as Adventure | null)?.visits.map(v => new Date(v.end_date || v.start_date)).sort((a,b) => +b - +a)[0]?.toISOString()?.split('T')[0] || '';
	if (!selectedDate) {
		selectedDate = new Date().toISOString().split('T')[0];
	}


	$: {
		if (currentAlbum) {
			immichImages = [];
			fetchAlbumAssets(currentAlbum);
		} else if (searchCategory === 'date' && selectedDate) {
			searchImmich();
		}
	}
	
	async function loadMoreImmich() {
		// The next URL returned by our API is a absolute url to API, but we need to use the relative path, to use the frontend api proxy.
		const url = new URL(immichNextURL);
		immichNextURL = url.pathname + url.search;
		return fetchAssets(immichNextURL, true);
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

	async function fetchAlbumAssets(album_id: string,) {
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
		return fetchAssets(`/api/integrations/immich/search/?${buildQueryParams()}`);
	}

</script>

<div class="mb-4">
	<label for="immich" class="block font-medium mb-2">
		{$t('immich.immich')}
		<img src={ImmichLogo} alt="Immich Logo" class="h-6 w-6 inline-block -mt-1" />
	</label>
	<div class="mt-4">
		<div class="join">
			<input
				on:click={() => (currentAlbum = '')}
				type="radio"
				class="join-item btn"
				bind:group={searchCategory}
				value="search"
				aria-label="Search"
			/>
			<input
				type="radio"
				class="join-item btn"
				bind:group={searchCategory}
				value="date"
				aria-label="Show by date"
			/>
			<input
				type="radio"
				class="join-item btn"
				bind:group={searchCategory}
				value="album"
				aria-label="Select Album"
			/>
		</div>
		<div>
			{#if searchCategory === 'search'}
				<form on:submit|preventDefault={searchImmich}>
					<input
						type="text"
						placeholder="Type here"
						bind:value={immichSearchValue}
						class="input input-bordered w-full max-w-xs"
					/>
					<button type="submit" class="btn btn-neutral mt-2">Search</button>
				</form>
			{:else if searchCategory === 'date'}
				<input
					type="date"
					bind:value={selectedDate}
					class="input input-bordered w-full max-w-xs mt-2"
				/>
			{:else if searchCategory === 'album'}
				<select class="select select-bordered w-full max-w-xs mt-2" bind:value={currentAlbum}>
					<option value="" disabled selected>Select an Album</option>
					{#each albums as album}
						<option value={album.id}>{album.albumName}</option>
					{/each}
				</select>
			{/if}
		</div>
	</div>

	<p class="text-red-500">{immichError}</p>
	<div class="flex flex-wrap gap-4 mr-4 mt-2">
		{#if loading}
		<div class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-[100] w-24 h-24">
			<span class="loading loading-spinner w-24 h-24"></span>
		</div>
		{/if}

		{#each immichImages as image}
			<div class="flex flex-col items-center gap-2" class:blur-sm={loading}>
				<!-- svelte-ignore a11y-img-redundant-alt -->
				<img
					src={`/immich/${image.id}`}
					alt="Image from Immich"
					class="h-24 w-24 object-cover rounded-md"
				/>
				<h4>
					{image.fileCreatedAt?.split('T')[0] || "Unknown"}
				</h4>
				<button
					type="button"
					class="btn btn-sm btn-primary"
					on:click={() => {
						let currentDomain = window.location.origin;
						let fullUrl = `${currentDomain}/immich/${image.id}`;
						dispatch('fetchImage', fullUrl);
					}}
				>
					{$t('adventures.upload_image')}
				</button>
			</div>
		{/each}
		{#if immichNextURL}
			<button class="btn btn-neutral" on:click={loadMoreImmich}>{$t('immich.load_more')}</button>
		{/if}
	</div>
</div>
