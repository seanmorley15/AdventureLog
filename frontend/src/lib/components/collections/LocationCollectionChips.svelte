<script lang="ts">
	import { onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import { addToast } from '#lib/toasts.js';
	import { fetchMembership, type CollectionMembership } from '#lib/collection-membership.js';
	import CollectionPicker from './CollectionPicker.svelte';
	import UnlinkPlaceDialog from './UnlinkPlaceDialog.svelte';
	import Folder from '~icons/mdi/folder-outline';
	import Close from '~icons/mdi/close';
	import Plus from '~icons/mdi/plus';

	interface Props {
		locationId: string;
		locationName?: string;
		/** Shows the add chip and the picker. */
		canManage?: boolean;
		/** Your uuid, so the unlink dialog says "you" for your own copy. */
		meUuid?: string | null;
	}

	let { locationId, locationName = '', canManage = false, meUuid = null }: Props = $props();

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

	// The row being taken out. The dialog asks the server what that would change first.
	let removing: CollectionMembership | null = $state(null);

	async function removed() {
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
						onclick={() => (removing = row)}
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
		{meUuid}
		onchange={load}
		onclose={() => (pickerOpen = false)}
	/>
{/if}

{#if removing}
	<UnlinkPlaceDialog
		{locationId}
		collectionId={removing.id}
		collectionName={removing.name}
		{meUuid}
		onunlinked={removed}
		onclose={() => (removing = null)}
	/>
{/if}
