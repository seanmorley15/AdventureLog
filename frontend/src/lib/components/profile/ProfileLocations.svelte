<script lang="ts">
	import { untrack } from 'svelte';
	import { t } from 'svelte-i18n';
	import LocationCard from '#lib/components/cards/LocationCard.svelte';
	import type { User } from '#lib/types.js';
	import type { LocationOrdering, LocationsPage } from './types.js';

	import MapMarkerOff from '~icons/mdi/map-marker-off-outline';
	import AlertCircle from '~icons/mdi/alert-circle-outline';

	interface Props {
		username: string;
		viewer: User | null;
		isOwn: boolean;
		/** The first page, streamed from the server. null when it failed to load. */
		initial: LocationsPage | null;
	}

	let { username, viewer, isOwn, initial }: Props = $props();

	const PAGE_SIZE = 12;

	// The first page only seeds the list; later pages are fetched here.
	const seed = untrack(() => initial);
	let items = $state(seed?.results ?? []);
	let total = $state(seed?.count ?? 0);
	let nextPage = $state<number | null>(seed?.next ? 2 : null);
	let failed = $state(seed === null);
	let loading = $state(false);
	let ordering = $state<LocationOrdering>('recent');
	// Guards against a slow response for an old ordering overwriting a newer one.
	let requestId = 0;

	async function fetchPage(page: number, replace: boolean) {
		const id = ++requestId;
		loading = true;
		try {
			const res = await fetch(
				`/api/users/${encodeURIComponent(username)}/locations/?page=${page}&page_size=${PAGE_SIZE}&ordering=${ordering}`
			);
			if (!res.ok) throw new Error(String(res.status));
			const body: LocationsPage = await res.json();
			if (id !== requestId) return;
			items = replace ? body.results : [...items, ...body.results];
			total = body.count;
			nextPage = body.next ? page + 1 : null;
			failed = false;
		} catch {
			if (id === requestId) failed = true;
		} finally {
			if (id === requestId) loading = false;
		}
	}

	function changeOrdering(event: Event) {
		ordering = (event.currentTarget as HTMLSelectElement).value as LocationOrdering;
		fetchPage(1, true);
	}
</script>

{#if failed && items.length === 0}
	<div
		class="flex flex-col items-center gap-3 rounded-box border border-base-300/60 bg-base-100 py-14 text-center"
	>
		<AlertCircle class="h-10 w-10 text-warning" />
		<p class="text-base-content/70">{$t('profile.section_failed')}</p>
		<button class="btn btn-sm btn-primary" onclick={() => fetchPage(1, true)} disabled={loading}>
			{#if loading}<span class="loading loading-spinner loading-xs"></span>{/if}
			{$t('profile.retry')}
		</button>
	</div>
{:else if total === 0 && !loading}
	<div
		class="flex flex-col items-center gap-3 rounded-box border border-base-300/60 bg-base-100 py-14 text-center"
	>
		<MapMarkerOff class="h-10 w-10 text-base-content/30" />
		<p class="max-w-md text-base-content/60">
			{isOwn ? $t('profile.no_locations_own') : $t('profile.no_shared_adventures')}
		</p>
	</div>
{:else}
	<div class="mb-4 flex items-center justify-between gap-3">
		<p class="text-sm text-base-content/60">
			{$t('profile.showing_of', { values: { shown: items.length, total } })}
		</p>
		<select
			class="select select-sm select-bordered w-auto"
			aria-label={$t('adventures.sort')}
			value={ordering}
			onchange={changeOrdering}
		>
			<option value="recent">{$t('profile.sort_recent')}</option>
			<option value="oldest">{$t('profile.sort_oldest')}</option>
			<option value="name">{$t('profile.sort_name')}</option>
			<option value="rating">{$t('profile.sort_rating')}</option>
		</select>
	</div>

	<div class="grid gap-5 sm:grid-cols-2 xl:grid-cols-3" aria-busy={loading}>
		{#each items as adventure (adventure.id)}
			<LocationCard {adventure} user={viewer} readOnly />
		{/each}
		{#if loading && items.length === 0}
			{#each Array(6) as _}
				<div class="skeleton h-72 rounded-box"></div>
			{/each}
		{/if}
	</div>

	{#if failed}
		<p class="mt-4 text-center text-sm text-warning">{$t('profile.section_failed')}</p>
	{/if}
	{#if nextPage}
		<div class="mt-6 flex justify-center">
			<button
				class="btn btn-outline"
				onclick={() => nextPage && fetchPage(nextPage, false)}
				disabled={loading}
			>
				{#if loading}<span class="loading loading-spinner loading-xs"></span>{/if}
				{failed ? $t('profile.retry') : $t('profile.load_more')}
			</button>
		</div>
	{/if}
{/if}
