<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import TrashCanOutline from '~icons/mdi/trash-can-outline';
	import FileDocumentEdit from '~icons/mdi/file-document-edit';
	import type { Collection, Transportation, User } from '$lib/types';
	import { addToast } from '$lib/toasts';
	import { t } from 'svelte-i18n';

	import ArrowDownThick from '~icons/mdi/arrow-down-thick';

	const dispatch = createEventDispatcher();

	export let transportation: Transportation;
	export let user: User | null = null;
	export let collection: Collection | null = null;

	function editTransportation() {
		dispatch('edit', transportation);
	}

	async function deleteTransportation() {
		let res = await fetch(`/api/transportations/${transportation.id}`, {
			method: 'DELETE',
			headers: {
				'Content-Type': 'application/json'
			}
		});
		if (!res.ok) {
			console.log($t('transportation.transportation_delete_error'));
		} else {
			addToast('info', $t('transportation.transportation_deleted'));
			dispatch('delete', transportation.id);
		}
	}
</script>

<div
	class="card w-full max-w-xs sm:max-w-sm md:max-w-md lg:max-w-md xl:max-w-md bg-neutral text-neutral-content shadow-xl"
>
	<div class="card-body">
		<h2 class="card-title overflow-ellipsis">{transportation.name}</h2>
		<div class="badge badge-secondary">{$t(`transportation.modes.${transportation.type}`)}</div>
		<div>
			{#if transportation.from_location}
				<p class="break-words text-wrap">{transportation.from_location}</p>
			{/if}
			{#if transportation.to_location}
				<ArrowDownThick class="w-6 h-6" />
				<p class="break-words text-wrap">{transportation.to_location}</p>
			{/if}
		</div>
		<div>
			{#if transportation.date}
				<p>{new Date(transportation.date).toLocaleString(undefined, { timeZone: 'UTC' })}</p>
			{/if}
			{#if transportation.end_date}
				<ArrowDownThick class="w-6 h-6" />
				<p>{new Date(transportation.end_date).toLocaleString(undefined, { timeZone: 'UTC' })}</p>
			{/if}
		</div>

		{#if transportation.user_id == user?.pk || (collection && user && collection.shared_with.includes(user.uuid))}
			<div class="card-actions justify-end">
				<button on:click={deleteTransportation} class="btn btn-secondary"
					><TrashCanOutline class="w-5 h-5 mr-1" /></button
				>
				<button class="btn btn-primary" on:click={editTransportation}>
					<FileDocumentEdit class="w-6 h-6" />
				</button>
			</div>
		{/if}
	</div>
</div>
