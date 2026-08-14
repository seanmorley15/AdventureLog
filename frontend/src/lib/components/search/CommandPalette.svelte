<script lang="ts">
	import { run } from 'svelte/legacy';

	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { debounce } from '$lib';
	import { searchPlaces } from '$lib/map/places';
	import { filterQuickNavActions, quickNavActions, type QuickNavAction } from '$lib/search/actions';
	import { searchApp } from '$lib/search/api';
	import {
		addRecentSearch,
		closeCommandPalette,
		commandPaletteInitialQuery,
		commandPaletteOpen,
		getRecentSearches
	} from '$lib/search/palette';
	import SearchResultRow from '$lib/search/SearchResultRow.svelte';
	import type { PaletteItem, SearchHit, SearchTab } from '$lib/search/types';
	import Magnify from '~icons/mdi/magnify';
	import MapMarker from '~icons/mdi/map-marker';
	import { onMount, tick } from 'svelte';
	import { t } from 'svelte-i18n';

	let inputElement: HTMLInputElement | null = $state(null);
	let query = $state('');
	let activeTab: SearchTab = $state('adventures');
	let selectedIndex = $state(0);
	let loading = $state(false);
	let error = $state('');
	let appResults: SearchHit[] = $state([]);
	let placeItems: Extract<PaletteItem, { kind: 'place' }>[] = $state([]);
	let recentSearches: string[] = $state([]);
	let searchAbort: AbortController | null = null;
	let scrollContainer: HTMLDivElement | null = $state(null);

	const paletteEntryClass =
		'w-full text-left flex items-center gap-3 mx-1 px-3 py-2.5 rounded-xl transition-colors mb-1.5 last:mb-0';
	const paletteEntryIdleClass = 'bg-base-200/25 hover:bg-base-200/45';

	function entryStateClass(selected: boolean): string {
		return selected ? 'bg-primary text-primary-content' : paletteEntryIdleClass;
	}


	function buildPaletteItems(
		tab: SearchTab,
		hits: SearchHit[],
		places: Extract<PaletteItem, { kind: 'place' }>[],
		includeActions: boolean,
		actions: QuickNavAction[]
	): PaletteItem[] {
		const items: PaletteItem[] = [];

		if (includeActions) {
			for (const action of actions) {
				items.push({ kind: 'action', action });
			}
		}

		if (tab === 'places') {
			return [...items, ...places];
		}

		for (const hit of hits) {
			items.push({ kind: 'hit', hit });
		}

		return items;
	}

	async function focusInput() {
		await tick();
		inputElement?.focus();
		inputElement?.select();
	}

	function closeDialog() {
		searchAbort?.abort();
		loading = false;
		error = '';
		query = '';
		activeTab = 'adventures';
		selectedIndex = 0;
		appResults = [];
		placeItems = [];
		closeCommandPalette();
	}

	function navigateTo(url: string, searchTerm = '') {
		if (searchTerm.trim().length >= 2) {
			addRecentSearch(searchTerm);
		}
		closeDialog();
		goto(url);
	}

	function handleSelectItem(item: PaletteItem) {
		if (item.kind === 'action') {
			navigateTo(item.action.url, query);
			return;
		}

		if (item.kind === 'place') {
			navigateTo(item.url, query);
			return;
		}

		navigateTo(item.hit.url, query);
	}

	function handleSeeAllResults() {
		const searchTerm = query.trim();
		if (searchTerm.length < 2) return;
		addRecentSearch(searchTerm);
		closeDialog();
		goto(`/search?q=${encodeURIComponent(searchTerm)}`);
	}

	async function scrollSelectedIntoView() {
		await tick();
		const selectedEl = scrollContainer?.querySelector(`[data-palette-index="${selectedIndex}"]`);
		selectedEl?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
	}

	const runSearch = debounce(async () => {
		searchAbort?.abort();
		error = '';

		const trimmed = query.trim();
		if (activeTab === 'adventures') {
			if (trimmed.length < 2 || trimmed.startsWith('>')) {
				appResults = [];
				loading = false;
				return;
			}

			loading = true;
			searchAbort = new AbortController();
			try {
				const response = await searchApp(trimmed, { limit: 8, signal: searchAbort.signal });
				appResults = response.results;
			} catch (err) {
				if ((err as Error).name !== 'AbortError') {
					error = (err as Error).message || 'Search failed';
					appResults = [];
				}
			} finally {
				loading = false;
			}
			return;
		}

		if (trimmed.length < 3) {
			placeItems = [];
			loading = false;
			return;
		}

		loading = true;
		try {
			const response = await searchPlaces(trimmed);
			placeItems = response.results.map((place) => ({
				kind: 'place' as const,
				id: place.id,
				title: place.name,
				subtitle: place.location,
				url: `/map?lat=${place.lat}&lng=${place.lng}&zoom=14`
			}));
		} catch (err) {
			error = (err as Error).message || 'Place search failed';
			placeItems = [];
		} finally {
			loading = false;
		}
	}, 300);




	function handleKeydown(event: KeyboardEvent) {
		if (!$commandPaletteOpen) return;

		if (event.key === 'Escape') {
			event.preventDefault();
			closeDialog();
			return;
		}

		if (event.key === 'Tab') {
			event.preventDefault();
			activeTab = activeTab === 'adventures' ? 'places' : 'adventures';
			return;
		}

		if (event.key === 'ArrowDown') {
			event.preventDefault();
			if (paletteItems.length === 0) return;
			selectedIndex = (selectedIndex + 1) % paletteItems.length;
			return;
		}

		if (event.key === 'ArrowUp') {
			event.preventDefault();
			if (paletteItems.length === 0) return;
			selectedIndex = (selectedIndex - 1 + paletteItems.length) % paletteItems.length;
			return;
		}

		if (event.key === 'Enter') {
			event.preventDefault();
			const item = paletteItems[selectedIndex];
			if (item) {
				handleSelectItem(item);
			}
		}
	}

	onMount(() => {
		const globalShortcut = (event: KeyboardEvent) => {
			if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
				event.preventDefault();
				if ($commandPaletteOpen) {
					closeDialog();
				} else {
					commandPaletteOpen.set(true);
				}
			}
		};

		document.addEventListener('keydown', globalShortcut);
		return () => document.removeEventListener('keydown', globalShortcut);
	});
	let isMac = $derived(browser && /Mac|iPhone|iPad/.test(navigator.platform));
	let modifierHint = $derived(isMac ? '⌘K' : 'Ctrl+K');
	run(() => {
		if ($commandPaletteOpen) {
			recentSearches = getRecentSearches();
			if ($commandPaletteInitialQuery) {
				query = $commandPaletteInitialQuery;
				commandPaletteInitialQuery.set('');
			}
			focusInput();
		}
	});
	let showActions = $derived(!query.trim() || query.trim().startsWith('>'));
	let filteredActions = $derived(filterQuickNavActions(query));
	let paletteItems = $derived(buildPaletteItems(
		activeTab,
		appResults,
		placeItems,
		showActions,
		filteredActions
	));
	run(() => {
		if ($commandPaletteOpen) {
			query;
			activeTab;
			runSearch();
			selectedIndex = 0;
		}
	});
	run(() => {
		if ($commandPaletteOpen && paletteItems.length > 0) {
			selectedIndex;
			scrollSelectedIntoView();
		}
	});
</script>

<svelte:window onkeydown={handleKeydown} />

{#if $commandPaletteOpen}
	<dialog class="modal modal-open backdrop-blur-md" aria-modal="true">
		<div
			class="modal-box max-w-3xl p-0 overflow-hidden rounded-2xl border border-base-content/10 bg-base-100/88 backdrop-blur-xl shadow-2xl shadow-base-content/10"
		>
			<div class="border-b border-base-content/10 px-5 py-4 bg-base-100/40">
				<div class="flex items-center gap-3">
					<Magnify class="w-5 h-5 opacity-50 shrink-0" />
					<input
						bind:this={inputElement}
						bind:value={query}
						type="text"
						class="input input-ghost w-full focus:outline-hidden pl-2 pr-0 text-lg h-12 min-h-0 bg-transparent"
						placeholder={$t('navbar.search')}
						autocomplete="off"
						spellcheck="false"
					/>
					<kbd class="kbd kbd-sm hidden sm:inline-flex opacity-70">{modifierHint}</kbd>
				</div>
				<div class="tabs tabs-box mt-4 bg-base-200/80 p-1 rounded-xl">
					<button
						type="button"
						class="tab flex-1"
						class:tab-active={activeTab === 'adventures'}
						onclick={() => (activeTab = 'adventures')}
					>
						{$t('search.tab_adventures')}
					</button>
					<button
						type="button"
						class="tab flex-1"
						class:tab-active={activeTab === 'places'}
						onclick={() => (activeTab = 'places')}
					>
						{$t('search.tab_places')}
					</button>
				</div>
			</div>

			<div
				bind:this={scrollContainer}
				class="max-h-[min(420px,50vh)] overflow-y-auto px-3 py-3 scroll-smooth bg-base-100/20"
			>
				{#if loading}
					<div class="px-4 py-10 text-center text-base-content/60">
						<span class="loading loading-spinner loading-md"></span>
					</div>
				{:else if error}
					<div class="px-4 py-6 text-center text-error">{error}</div>
				{:else if paletteItems.length === 0 && !query.trim()}
					<div class="px-2 py-1">
						<p class="text-xs font-semibold uppercase tracking-wide text-base-content/50 px-3 py-2">
							{$t('search.quick_actions')}
						</p>
						{#each quickNavActions as action, index}
							<button
								type="button"
								data-palette-index={index}
								class={`${paletteEntryClass} ${entryStateClass(selectedIndex === index)}`}
								onclick={() => navigateTo(action.url)}
							>
								<div
									class="flex h-10 w-10 items-center justify-center rounded-xl shrink-0"
									class:bg-primary-content={selectedIndex === index}
									class:text-primary={selectedIndex === index}
									class:bg-base-200={selectedIndex !== index}
								>
									<action.icon class="w-5 h-5" />
								</div>
								<div class="min-w-0 flex-1">
									<div class="font-medium leading-snug">{$t(action.titleKey)}</div>
									<p class="text-sm opacity-70 leading-snug mt-0.5">{$t(action.subtitleKey)}</p>
								</div>
							</button>
						{/each}

						{#if recentSearches.length > 0}
							<p
								class="text-xs font-semibold uppercase tracking-wide text-base-content/50 px-3 py-2 mt-3"
							>
								{$t('search.recent_searches')}
							</p>
							{#each recentSearches as recentQuery}
								<button
									type="button"
									class="w-full text-left mx-1 px-3 py-2 rounded-lg hover:bg-base-200 truncate text-sm"
									onclick={() => {
										query = recentQuery;
									}}
								>
									{recentQuery}
								</button>
							{/each}
						{/if}
					</div>
				{:else if paletteItems.length === 0}
					<div class="px-4 py-8 text-center text-base-content/60">
						{#if activeTab === 'places' && query.trim().length > 0 && query.trim().length < 3}
							{$t('search.places_min_chars')}
						{:else if query.trim().startsWith('>')}
							{$t('search.no_actions')}
						{:else}
							{$t('adventures.no_results')}
						{/if}
					</div>
				{:else}
					{#each paletteItems as item, index}
						{#if item.kind === 'action'}
							{#if index === 0 && showActions}
								<p
									class="text-xs font-semibold uppercase tracking-wide text-base-content/50 px-3 py-2"
								>
									{$t('search.quick_actions')}
								</p>
							{/if}
							<button
								type="button"
								data-palette-index={index}
								class={`${paletteEntryClass} ${entryStateClass(selectedIndex === index)}`}
								onclick={() => handleSelectItem(item)}
							>
								<div
									class="flex h-10 w-10 items-center justify-center rounded-xl shrink-0"
									class:bg-primary-content={selectedIndex === index}
									class:text-primary={selectedIndex === index}
									class:bg-base-200={selectedIndex !== index}
								>
									<item.action.icon class="w-5 h-5" />
								</div>
								<div class="min-w-0 flex-1">
									<div class="font-medium leading-snug">{$t(item.action.titleKey)}</div>
									<p class="text-sm opacity-70 leading-snug mt-0.5">
										{$t(item.action.subtitleKey)}
									</p>
								</div>
							</button>
						{:else if item.kind === 'hit'}
							{#if index === filteredActions.length && showActions && filteredActions.length > 0}
								<p
									class="text-xs font-semibold uppercase tracking-wide text-base-content/50 px-3 py-2 mt-1"
								>
									{$t('search.results_heading')}
								</p>
							{:else if index === 0 && !showActions}
								<p
									class="text-xs font-semibold uppercase tracking-wide text-base-content/50 px-3 py-2"
								>
									{$t('search.results_heading')}
								</p>
							{/if}
							<div data-palette-index={index} class="mb-1.5 last:mb-0">
								<SearchResultRow
									hit={item.hit}
									selected={selectedIndex === index}
									spotlight
									on:select={() => handleSelectItem(item)}
								/>
							</div>
						{:else}
							{#if index === filteredActions.length && showActions && filteredActions.length > 0}
								<p
									class="text-xs font-semibold uppercase tracking-wide text-base-content/50 px-3 py-2 mt-1"
								>
									{$t('search.places_heading')}
								</p>
							{:else if index === 0}
								<p
									class="text-xs font-semibold uppercase tracking-wide text-base-content/50 px-3 py-2"
								>
									{$t('search.places_heading')}
								</p>
							{/if}
							<button
								type="button"
								data-palette-index={index}
								class={`${paletteEntryClass} ${entryStateClass(selectedIndex === index)}`}
								onclick={() => handleSelectItem(item)}
							>
								<div
									class="flex h-10 w-10 items-center justify-center rounded-xl shrink-0"
									class:bg-primary-content={selectedIndex === index}
									class:text-primary={selectedIndex === index}
									class:bg-base-200={selectedIndex !== index}
								>
									<MapMarker class="w-5 h-5" />
								</div>
								<div class="min-w-0 flex-1">
									<div class="font-medium truncate leading-snug">{item.title}</div>
									{#if item.subtitle}
										<p class="text-sm truncate opacity-70 leading-snug mt-0.5">{item.subtitle}</p>
									{/if}
								</div>
							</button>
						{/if}
					{/each}

					{#if !query.trim() && recentSearches.length > 0}
						<p class="text-sm font-semibold text-base-content/60 mt-4 mb-2 px-2">
							{$t('search.recent_searches')}
						</p>
						{#each recentSearches as recentQuery}
							<button
								type="button"
								class="w-full text-left px-4 py-2 rounded-lg hover:bg-base-200 truncate"
								onclick={() => {
									query = recentQuery;
								}}
							>
								{recentQuery}
							</button>
						{/each}
					{/if}
				{/if}
			</div>

			<div
				class="border-t border-base-content/10 px-5 py-3.5 flex items-center justify-between gap-3 bg-base-100/35 backdrop-blur-xs"
			>
				<div class="text-xs text-base-content/60 hidden sm:flex gap-3">
					<span>↑↓ {$t('search.navigate')}</span>
					<span>↵ {$t('search.open')}</span>
					<span>Tab {$t('search.switch_tab')}</span>
				</div>
				{#if activeTab === 'adventures' && query.trim().length >= 2 && !query
						.trim()
						.startsWith('>')}
					<button
						type="button"
						class="btn btn-primary btn-sm ml-auto"
						onclick={handleSeeAllResults}
					>
						{$t('search.see_all_results')}
					</button>
				{/if}
			</div>
		</div>
		<button
			type="button"
			class="modal-backdrop bg-black/30 backdrop-blur-[2px]"
			aria-label={$t('search.close')}
			onclick={closeDialog}
		></button>
	</dialog>
{/if}
