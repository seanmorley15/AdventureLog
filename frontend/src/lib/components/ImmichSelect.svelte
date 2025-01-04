<script lang="ts">
	let immichSearchValue: string = '';
	let searchOrSelect: string = 'search';
	let immichError: string = '';
	let immichNext: string = '';
	let immichPage: number = 1;

	import { createEventDispatcher, onMount } from 'svelte';
	const dispatch = createEventDispatcher();

	let albums: ImmichAlbum[] = [];
	let currentAlbum: string = '';

	$: {
		if (currentAlbum) {
			immichImages = [];
			fetchAlbumAssets(currentAlbum);
		} else {
			immichImages = [];
		}
	}

	async function fetchAlbumAssets(album_id: string) {
		let res = await fetch(`/api/integrations/immich/albums/${album_id}`);
		if (res.ok) {
			let data = await res.json();
			immichNext = '';
			immichImages = data;
		}
	}

	onMount(async () => {
		let res = await fetch('/api/integrations/immich/albums');
		if (res.ok) {
			let data = await res.json();
			albums = data;
		}
	});

	let immichImages: any[] = [];
	import { t } from 'svelte-i18n';
	import ImmichLogo from '$lib/assets/immich.svg';
	import type { ImmichAlbum } from '$lib/types';

	async function searchImmich() {
		let res = await fetch(`/api/integrations/immich/search/?query=${immichSearchValue}`);
		if (!res.ok) {
			let data = await res.json();
			let errorMessage = data.message;
			console.log(errorMessage);
			immichError = $t(data.code);
		} else {
			let data = await res.json();
			console.log(data);
			immichError = '';
			if (data.results && data.results.length > 0) {
				immichImages = data.results;
			} else {
				immichError = $t('immich.no_items_found');
			}
			if (data.next) {
				immichNext =
					'/api/integrations/immich/search?query=' +
					immichSearchValue +
					'&page=' +
					(immichPage + 1);
			} else {
				immichNext = '';
			}
		}
	}

	async function loadMoreImmich() {
		let res = await fetch(immichNext);
		if (!res.ok) {
			let data = await res.json();
			let errorMessage = data.message;
			console.log(errorMessage);
			immichError = $t(data.code);
		} else {
			let data = await res.json();
			console.log(data);
			immichError = '';
			if (data.results && data.results.length > 0) {
				immichImages = [...immichImages, ...data.results];
			} else {
				immichError = $t('immich.no_items_found');
			}
			if (data.next) {
				immichNext =
					'/api/integrations/immich/search?query=' +
					immichSearchValue +
					'&page=' +
					(immichPage + 1);
				immichPage++;
			} else {
				immichNext = '';
			}
		}
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
				bind:group={searchOrSelect}
				value="search"
				aria-label="Search"
			/>
			<input
				type="radio"
				class="join-item btn"
				bind:group={searchOrSelect}
				value="select"
				aria-label="Select Album"
			/>
		</div>
		<div>
			{#if searchOrSelect === 'search'}
				<form on:submit|preventDefault={searchImmich}>
					<input
						type="text"
						placeholder="Type here"
						bind:value={immichSearchValue}
						class="input input-bordered w-full max-w-xs"
					/>
					<button type="submit" class="btn btn-neutral mt-2">Search</button>
				</form>
			{:else}
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
		{#each immichImages as image}
			<div class="flex flex-col items-center gap-2">
				<!-- svelte-ignore a11y-img-redundant-alt -->
				<img
					src={`/immich/${image.id}`}
					alt="Image from Immich"
					class="h-24 w-24 object-cover rounded-md"
				/>
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
		{#if immichNext}
			<button class="btn btn-neutral" on:click={loadMoreImmich}>{$t('immich.load_more')}</button>
		{/if}
	</div>
</div>
