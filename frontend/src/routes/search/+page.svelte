<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { searchApp } from '$lib/search/api';
	import SearchResultRow from '$lib/search/SearchResultRow.svelte';
	import { openCommandPalette } from '$lib/search/palette';
	import type { SearchEntityType, SearchHit } from '$lib/search/types';
	import type { PageData } from './$types';
	import Magnify from '~icons/mdi/magnify';
	import { t } from 'svelte-i18n';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	type SearchFilter = {
		id: string;
		labelKey: string;
		types?: SearchEntityType[];
	};

	const filters: SearchFilter[] = [
		{ id: 'all', labelKey: 'search.filters.all' },
		{
			id: 'adventures',
			labelKey: 'search.filters.adventures',
			types: ['location']
		},
		{
			id: 'collections',
			labelKey: 'search.filters.collections',
			types: ['collection', 'lodging', 'transportation', 'note', 'checklist', 'activity']
		},
		{
			id: 'notes',
			labelKey: 'search.filters.notes',
			types: ['note', 'checklist']
		},
		{
			id: 'transport',
			labelKey: 'search.filters.transport',
			types: ['transportation', 'lodging']
		},
		{
			id: 'world',
			labelKey: 'search.filters.world',
			types: ['country', 'region', 'city']
		},
		{ id: 'users', labelKey: 'search.filters.users', types: ['user'] }
	];

	let results: SearchHit[] = $state<SearchHit[]>([]);
	let total = $state(0);
	let offset = $state(0);
	let limit = $state(0);
	let loadingMore = $state(false);
	let loadMoreError = $state('');

	let query = $derived($page.url.searchParams.get('q') || $page.url.searchParams.get('query') || '');
	let activeFilter = $derived($page.url.searchParams.get('filter') || 'all');
	let hasQuery = $derived(query.trim().length > 0);
	let hasResults = $derived(results.length > 0);
	let canLoadMore = $derived(hasQuery && results.length < total);

	$effect.pre(() => {
		results = data.results;
		total = data.total;
		offset = data.offset;
		limit = data.limit;
	});

	function getFilterTypes(filterId: string): SearchEntityType[] | undefined {
		return filters.find((filter) => filter.id === filterId)?.types;
	}

	function applyFilter(filterId: string) {
		const url = new URL(window.location.href);
		if (filterId === 'all') {
			url.searchParams.delete('filter');
			url.searchParams.delete('types');
		} else {
			url.searchParams.set('filter', filterId);
			const types = getFilterTypes(filterId);
			if (types?.length) {
				url.searchParams.set('types', types.join(','));
			}
		}
		goto(url.toString(), { invalidateAll: true });
	}

	async function loadMore() {
		if (!hasQuery || loadingMore || !canLoadMore) return;

		loadingMore = true;
		loadMoreError = '';
		const nextOffset = offset + limit;
		const types = getFilterTypes(activeFilter);

		try {
			const response = await searchApp(query, {
				types,
				limit,
				offset: nextOffset
			});
			results = [...results, ...response.results];
			total = response.total;
			offset = response.offset;
		} catch (err) {
			loadMoreError = (err as Error).message || 'Failed to load more results';
		} finally {
			loadingMore = false;
		}
	}
</script>

<svelte:head>
	<title>{hasQuery ? `Search: ${query}` : 'Search'} | AdventureLog</title>
	<meta
		name="description"
		content={hasQuery
			? `AdventureLog search results for ${query}`
			: 'Search your adventures, collections, and travel data in AdventureLog'}
	/>
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-base-200 via-base-100 to-base-200">
	<div class="sticky top-0 z-40 bg-base-100/80 backdrop-blur-lg border-b border-base-300">
		<div class="container mx-auto px-6 py-4">
			<div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
				<div class="flex items-center gap-3">
					<div class="p-2 bg-primary/10 rounded-xl">
						<Magnify class="w-8 h-8 text-primary" />
					</div>
					<div>
						<h1
							class="text-3xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent"
						>
							{$t('navbar.search')}{hasQuery ? `: ${query}` : ''}
						</h1>
						{#if hasQuery && hasResults}
							<p class="text-sm text-base-content/60">
								{total}
								{total !== 1 ? $t('search.results') : $t('search.result')}
								{$t('search.found')}
							</p>
						{/if}
					</div>
				</div>

				<button
					type="button"
					class="btn btn-primary btn-sm lg:btn-md"
					onclick={() => openCommandPalette(query)}
				>
					{$t('search.open_palette')}
				</button>
			</div>

			{#if hasQuery}
				<div class="flex flex-wrap gap-2 mt-4">
					{#each filters as filter}
						<button
							type="button"
							class="btn btn-sm"
							class:btn-primary={activeFilter === filter.id}
							class:btn-ghost={activeFilter !== filter.id}
							onclick={() => applyFilter(filter.id)}
						>
							{$t(filter.labelKey)}
						</button>
					{/each}
				</div>
			{/if}
		</div>
	</div>

	<div class="container mx-auto px-6 py-8 max-w-3xl">
		{#if data.error}
			<div class="alert alert-error mb-6">
				<span>{data.error}</span>
				<button
					type="button"
					class="btn btn-sm"
					onclick={() => goto($page.url.pathname + $page.url.search)}
				>
					{$t('search.retry')}
				</button>
			</div>
		{:else if !hasQuery}
			<div class="flex flex-col items-center justify-center py-16 text-center">
				<div class="p-6 bg-base-200/50 rounded-2xl mb-6">
					<Magnify class="w-16 h-16 text-base-content/30" />
				</div>
				<h3 class="text-xl font-semibold text-base-content/70 mb-2">
					{$t('search.empty_prompt_title')}
				</h3>
				<p class="text-base-content/50 max-w-md mb-6">
					{$t('search.empty_prompt_desc')}
				</p>
				<button type="button" class="btn btn-primary" onclick={() => openCommandPalette()}>
					{$t('search.open_palette')}
				</button>
			</div>
		{:else if !hasResults}
			<div class="flex flex-col items-center justify-center py-16 text-center">
				<div class="p-6 bg-base-200/50 rounded-2xl mb-6">
					<Magnify class="w-16 h-16 text-base-content/30" />
				</div>
				<h3 class="text-xl font-semibold text-base-content/70 mb-2">
					{$t('adventures.no_results')}
				</h3>
				<p class="text-base-content/50 max-w-md">
					{$t('search.try_searching_desc')}
				</p>
			</div>
		{:else}
			<div
				class="bg-base-100 border border-base-300 rounded-2xl overflow-hidden shadow-xs divide-y divide-base-300"
			>
				{#each results as hit (hit.type + hit.id)}
					<SearchResultRow {hit} spotlight on:select={() => goto(hit.url)} />
				{/each}
			</div>

			{#if loadMoreError}
				<div class="alert alert-error mt-4">{loadMoreError}</div>
			{/if}

			{#if canLoadMore}
				<div class="flex justify-center mt-6">
					<button type="button" class="btn btn-outline" disabled={loadingMore} onclick={loadMore}>
						{#if loadingMore}
							<span class="loading loading-spinner loading-sm"></span>
						{/if}
						{$t('search.load_more')}
					</button>
				</div>
			{/if}
		{/if}
	</div>
</div>
