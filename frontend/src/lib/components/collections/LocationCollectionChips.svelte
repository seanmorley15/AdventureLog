<script lang="ts">
	import { onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import { addToast } from '#lib/toasts.js';
	import {
		fetchMembership,
		unlinkLocationFromCollection,
		type CollectionMembership
	} from '#lib/collection-membership.js';
	import CollectionPicker from './CollectionPicker.svelte';
	import Folder from '~icons/mdi/folder-outline';
	import Close from '~icons/mdi/close';
	import Plus from '~icons/mdi/plus';

	interface Props {
		locationId: string;
		locationName?: string;
		/** Shows the add chip and the picker. */
		canManage?: boolean;
	}

	let { locationId, locationName = '', canManage = false }: Props = $props();

	let rows: CollectionMembership[] = $state([]);
	let pickerOpen = $state(false);
	let linked = $derived(rows.filter((r) => r.is_linked));

	async function load() {
		try {
			rows = await fetchMembership(locationId);
		} catch {
			rows = [];
		}
	}

	onMount(load);

	async function remove(row: CollectionMembership) {
		if (
			row.placements.length > 0 &&
			!confirm(
				$t('collection.unlink_plan_warning', {
					values: { days: String(row.placements.length), name: row.name }
				})
			)
		) {
			return;
		}
		const removed = await unlinkLocationFromCollection(locationId, row.id);
		if (removed === null) {
			addToast('error', $t('adventures.collection_remove_location_error'));
			return;
		}
		addToast('info', $t('adventures.collection_remove_location_success'));
		await load();
	}
</script>

{#if linked.length > 0 || canManage}
	<div class="flex flex-wrap items-center gap-2">
		{#each linked as row (row.id)}
			<span class="badge badge-lg gap-1 pr-1">
				<Folder class="h-4 w-4" />
				<a href="/collections/{row.id}" class="link link-hover">{row.name}</a>
				{#if row.can_unlink}
					<button
						type="button"
						class="btn btn-ghost btn-xs btn-circle h-5 min-h-0 w-5"
						aria-label={$t('collection.remove_from_named', { values: { name: row.name } })}
						onclick={() => remove(row)}
					>
						<Close class="h-3 w-3" />
					</button>
				{/if}
			</span>
		{/each}
		{#if canManage}
			<button
				type="button"
				class="badge badge-lg badge-outline gap-1"
				onclick={() => (pickerOpen = true)}
			>
				<Plus class="h-4 w-4" />
				{$t('adventures.add_to_collection')}
			</button>
		{/if}
	</div>
{/if}

{#if pickerOpen}
	<CollectionPicker
		{locationId}
		{locationName}
		onchange={load}
		onclose={() => (pickerOpen = false)}
	/>
{/if}
