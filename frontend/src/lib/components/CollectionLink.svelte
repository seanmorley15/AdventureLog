<script lang="ts">
	import type { Adventure, Collection } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	import CollectionCard from './CollectionCard.svelte';
	let modal: HTMLDialogElement;
	import { t } from 'svelte-i18n';

	// Icons - following the worldtravel pattern
	import Collections from '~icons/mdi/folder-multiple';
	import Search from '~icons/mdi/magnify';
	import Clear from '~icons/mdi/close';
	import Link from '~icons/mdi/link-variant';

	let collections: Collection[] = [];
	let filteredCollections: Collection[] = [];
	let searchQuery: string = '';

	export let linkedCollectionList: string[] | null = null;

	// Search functionality following worldtravel pattern
	$: {
		if (searchQuery === '') {
			filteredCollections = collections;
		} else {
			filteredCollections = collections.filter((collection) =>
				collection.name.toLowerCase().includes(searchQuery.toLowerCase())
			);
		}
	}

	onMount(async () => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}

		let res = await fetch(`/api/collections/all/`, {
			method: 'GET'
		});

		let result = await res.json();

		if (result.type === 'success' && result.data) {
			collections = result.data.adventures as Collection[];
		} else {
			collections = result as Collection[];
		}

		// Move linked collections to the front
		if (linkedCollectionList) {
			collections.sort((a, b) => {
				const aLinked = linkedCollectionList?.includes(a.id);
				const bLinked = linkedCollectionList?.includes(b.id);
				return aLinked === bLinked ? 0 : aLinked ? -1 : 1;
			});
		}

		filteredCollections = collections;
	});

	function close() {
		dispatch('close');
	}

	function link(event: CustomEvent<string>) {
		dispatch('link', event.detail);
	}

	function unlink(event: CustomEvent<string>) {
		dispatch('unlink', event.detail);
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			dispatch('close');
		}
	}

	// Statistics following worldtravel pattern
	$: linkedCount = linkedCollectionList ? linkedCollectionList.length : 0;
	$: totalCollections = collections.length;
</script>

<dialog id="my_modal_1" class="modal backdrop-blur-sm">
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<div
		class="modal-box w-11/12 max-w-6xl bg-gradient-to-br from-base-100 via-base-100 to-base-200 border border-base-300 shadow-2xl"
		role="dialog"
		on:keydown={handleKeydown}
		tabindex="0"
	>
		<!-- Header Section - Following worldtravel pattern -->
		<div
			class="sticky top-0 z-10 bg-base-100/90 backdrop-blur-lg border-b border-base-300 -mx-6 -mt-6 px-6 py-4 mb-6"
		>
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-3">
					<div class="p-2 bg-primary/10 rounded-xl">
						<Collections class="w-8 h-8 text-primary" />
					</div>
					<div>
						<h1 class="text-3xl font-bold text-black bg-clip-text">
							{$t('adventures.my_collections')}
						</h1>
						<p class="text-sm text-base-content/60">
							{filteredCollections.length}
							{$t('worldtravel.of')}
							{totalCollections}
							{$t('navbar.collections')}
						</p>
					</div>
				</div>

				<!-- Quick Stats -->
				<div class="hidden md:flex items-center gap-2">
					<div class="stats stats-horizontal bg-base-200/50 border border-base-300/50">
						<div class="stat py-2 px-4">
							<div class="stat-title text-xs">{$t('collection.linked')}</div>
							<div class="stat-value text-lg text-success">{linkedCount}</div>
						</div>
						<div class="stat py-2 px-4">
							<div class="stat-title text-xs">{$t('collection.available')}</div>
							<div class="stat-value text-lg text-info">{totalCollections}</div>
						</div>
					</div>
				</div>

				<!-- Close Button -->
				<button class="btn btn-ghost btn-square" on:click={close}>
					<Clear class="w-5 h-5" />
				</button>
			</div>

			<!-- Search Bar -->
			<div class="mt-4 flex items-center gap-4">
				<div class="relative flex-1 max-w-md">
					<Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-base-content/40" />
					<input
						type="text"
						placeholder={$t('navbar.search')}
						class="input input-bordered w-full pl-10 pr-10 bg-base-100/80"
						bind:value={searchQuery}
					/>
					{#if searchQuery.length > 0}
						<button
							class="absolute right-3 top-1/2 -translate-y-1/2 text-base-content/40 hover:text-base-content"
							on:click={() => (searchQuery = '')}
						>
							<Clear class="w-4 h-4" />
						</button>
					{/if}
				</div>

				{#if searchQuery}
					<button class="btn btn-ghost btn-xs gap-1" on:click={() => (searchQuery = '')}>
						<Clear class="w-3 h-3" />
						{$t('worldtravel.clear_all')}
					</button>
				{/if}
			</div>
		</div>

		<!-- Main Content -->
		<div class="px-2">
			{#if filteredCollections.length === 0}
				<div class="flex flex-col items-center justify-center py-16">
					<div class="p-6 bg-base-200/50 rounded-2xl mb-6">
						<Collections class="w-16 h-16 text-base-content/30" />
					</div>
					{#if searchQuery}
						<h3 class="text-xl font-semibold text-base-content/70 mb-2">
							{$t('adventures.no_collections_found')}
						</h3>
						<p class="text-base-content/50 text-center max-w-md mb-6">
							{$t('collection.try_different_search')}
						</p>
						<button class="btn btn-primary gap-2" on:click={() => (searchQuery = '')}>
							<Clear class="w-4 h-4" />
							{$t('worldtravel.clear_filters')}
						</button>
					{:else}
						<h3 class="text-xl font-semibold text-base-content/70 mb-2">
							{$t('adventures.no_collections_found')}
						</h3>
						<p class="text-base-content/50 text-center max-w-md">
							{$t('adventures.create_collection_first')}
						</p>
					{/if}
				</div>
			{:else}
				<!-- Collections Grid -->
				<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-6 p-4">
					{#each filteredCollections as collection}
						<CollectionCard
							{collection}
							type="link"
							on:link={link}
							bind:linkedCollectionList
							on:unlink={unlink}
							user={null}
						/>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Footer Actions -->
		<div
			class="sticky bottom-0 bg-base-100/90 backdrop-blur-lg border-t border-base-300 -mx-6 -mb-6 px-6 py-4 mt-6"
		>
			<div class="flex items-center justify-between">
				<div class="text-sm text-base-content/60">
					{linkedCount}
					{$t('adventures.collections_linked')}
				</div>
				<button class="btn btn-primary gap-2" on:click={close}>
					<Link class="w-4 h-4" />
					{$t('adventures.done')}
				</button>
			</div>
		</div>
	</div>
</dialog>
