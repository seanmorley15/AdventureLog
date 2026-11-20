<script lang="ts">
	import { onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import { addToast } from '#lib/toasts.js';
	import {
		fetchMembership,
		linkLocationToCollection,
		placementDays,
		unlinkLocationFromCollection,
		type CollectionMembership
	} from '#lib/collection-membership.js';

	import Collections from '~icons/mdi/folder-multiple';
	import Search from '~icons/mdi/magnify';
	import Clear from '~icons/mdi/close';
	import Share from '~icons/mdi/share-variant';

	interface Props {
		locationId: string;
		locationName?: string;
		onchange?: (collectionIds: string[]) => void;
		onclose: () => void;
	}

	let { locationId, locationName = '', onchange, onclose }: Props = $props();

	let dialog: HTMLDialogElement | undefined = $state();
	let rows: CollectionMembership[] = $state([]);
	let query = $state('');
	let loading = $state(true);
	let failed = $state(false);
	let busy: Record<string, boolean> = $state({});
	let search: ReturnType<typeof setTimeout> | undefined;

	let linked = $derived(rows.filter((r) => r.is_linked));
	let others = $derived(rows.filter((r) => !r.is_linked));
	let ownOthers = $derived(others.filter((r) => !r.is_shared));
	let sharedOthers = $derived(others.filter((r) => r.is_shared));

	function days(row: CollectionMembership) {
		return placementDays(
			row.placements,
			(n) => $t('itinerary.day_n', { values: { n } }),
			$t('itinerary.trip_wide'),
			$t('itinerary.ideas')
		);
	}

	async function load() {
		loading = true;
		failed = false;
		try {
			rows = await fetchMembership(locationId, query.trim());
		} catch {
			failed = true;
		} finally {
			loading = false;
		}
	}

	function onSearch() {
		clearTimeout(search);
		search = setTimeout(load, 250);
	}

	onMount(() => {
		dialog?.showModal();
		load();
		return () => clearTimeout(search);
	});

	function emit() {
		onchange?.(rows.filter((r) => r.is_linked).map((r) => r.id));
	}

	async function toggle(row: CollectionMembership) {
		if (busy[row.id]) return;
		const unlinking = row.is_linked;
		if (unlinking && row.placements.length > 0) {
			const ok = confirm(
				$t('collection.unlink_plan_warning', { values: { days: days(row), name: row.name } })
			);
			if (!ok) return;
		}
		busy[row.id] = true;
		const wasPlacements = row.placements;
		if (unlinking) {
			const removed = await unlinkLocationFromCollection(locationId, row.id);
			if (removed === null) {
				addToast('error', $t('adventures.collection_remove_location_error'));
			} else {
				row.is_linked = false;
				row.placements = [];
				addToast('info', $t('adventures.collection_remove_location_success'));
				emit();
			}
		} else {
			const ok = await linkLocationToCollection(locationId, row.id);
			if (!ok) {
				addToast('error', $t('adventures.collection_link_location_error'));
				row.placements = wasPlacements;
			} else {
				row.is_linked = true;
				addToast('info', $t('adventures.collection_link_location_success'));
				emit();
			}
		}
		busy[row.id] = false;
	}

	function dates(row: CollectionMembership) {
		if (!row.start_date) return '';
		const fmt = (d: string) => new Date(d).toLocaleDateString(undefined, { timeZone: 'UTC' });
		return row.end_date ? `${fmt(row.start_date)} – ${fmt(row.end_date)}` : fmt(row.start_date);
	}
</script>

{#snippet rowItem(row: CollectionMembership)}
	{@const disabled = row.is_linked ? !row.can_unlink : !row.can_link}
	<li>
		<label
			class="flex items-start gap-3 rounded-lg px-3 py-2 hover:bg-base-200"
			class:opacity-50={disabled}
			class:cursor-not-allowed={disabled}
			class:cursor-pointer={!disabled}
			title={disabled ? $t('collection.no_permission_membership') : undefined}
		>
			{#if busy[row.id]}
				<span class="loading loading-spinner loading-sm mt-0.5"></span>
			{:else}
				<input
					type="checkbox"
					class="checkbox checkbox-primary checkbox-sm mt-1"
					checked={row.is_linked}
					{disabled}
					onchange={() => toggle(row)}
				/>
			{/if}
			<span class="min-w-0 flex-1">
				<span class="flex items-center gap-2">
					<span class="truncate font-medium">{row.name}</span>
					{#if row.is_shared}
						<span class="badge badge-warning badge-sm gap-1">
							<Share class="h-3 w-3" />
							{row.owner_name}
						</span>
					{/if}
				</span>
				{#if dates(row)}
					<span class="block text-xs text-base-content/60">{dates(row)}</span>
				{/if}
				{#if row.is_linked && row.placements.length > 0}
					<span class="block text-xs text-info">
						{$t('collection.on_plan')} · {days(row)}
					</span>
				{/if}
			</span>
		</label>
	</li>
{/snippet}

{#snippet section(title: string, items: CollectionMembership[])}
	{#if items.length > 0}
		<div class="mb-4">
			<h3 class="px-3 pb-1 text-xs font-semibold uppercase tracking-wide text-base-content/60">
				{title}
				<span class="badge badge-ghost badge-xs ml-1">{items.length}</span>
			</h3>
			<ul>
				{#each items as row (row.id)}
					{@render rowItem(row)}
				{/each}
			</ul>
		</div>
	{/if}
{/snippet}

<dialog bind:this={dialog} class="modal backdrop-blur-xs" {onclose}>
	<div class="modal-box flex max-h-[85vh] w-11/12 max-w-lg flex-col p-0">
		<div class="border-b border-base-300 p-4">
			<div class="flex items-start justify-between gap-3">
				<div class="flex min-w-0 items-center gap-3">
					<div class="rounded-xl bg-primary/10 p-2">
						<Collections class="h-6 w-6 text-primary" />
					</div>
					<div class="min-w-0">
						<h2 class="text-lg font-bold">{$t('collection.manage_collections')}</h2>
						{#if locationName}
							<p class="truncate text-sm text-base-content/60">{locationName}</p>
						{/if}
					</div>
				</div>
				<button class="btn btn-ghost btn-sm btn-square" aria-label="close" onclick={onclose}>
					<Clear class="h-5 w-5" />
				</button>
			</div>
			<p class="mt-3 text-sm text-base-content/70">
				{$t('collection.in_n_collections', { values: { count: linked.length } })}
			</p>
			<div class="relative mt-3">
				<Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-base-content/40" />
				<input
					type="text"
					class="input input-sm w-full pl-9"
					placeholder={$t('navbar.search')}
					bind:value={query}
					oninput={onSearch}
				/>
			</div>
		</div>

		<div class="flex-1 overflow-y-auto p-2">
			{#if loading && rows.length === 0}
				<div class="flex justify-center py-12">
					<span class="loading loading-spinner loading-lg text-primary"></span>
				</div>
			{:else if failed}
				<p class="py-10 text-center text-error">
					{$t('adventures.collection_link_location_error')}
				</p>
			{:else if rows.length === 0}
				<p class="py-10 text-center text-base-content/60">
					{query
						? $t('collection.try_different_search')
						: $t('adventures.no_collections_to_add_location')}
				</p>
			{:else}
				{@render section($t('collection.in_these_collections'), linked)}
				{@render section($t('adventures.my_collections'), ownOthers)}
				{@render section($t('navbar.shared_with_me'), sharedOthers)}
			{/if}
		</div>

		<div class="flex justify-end border-t border-base-300 p-3">
			<button class="btn btn-primary btn-sm" onclick={onclose}>{$t('adventures.done')}</button>
		</div>
	</div>
	<form method="dialog" class="modal-backdrop"><button>close</button></form>
</dialog>
