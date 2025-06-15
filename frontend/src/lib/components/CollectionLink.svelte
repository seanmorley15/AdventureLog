<script lang="ts">
	import type { Adventure, Collection } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	import CollectionCard from './CollectionCard.svelte';
	let modal: HTMLDialogElement;
	import { t } from 'svelte-i18n';

	let collections: Collection[] = [];

	export let linkedCollectionList: string[] | null = null;

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
</script>

<dialog id="my_modal_1" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<div class="modal-box w-11/12 max-w-5xl" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<h1 class="text-center font-bold text-4xl mb-6">{$t('adventures.my_collections')}</h1>
		<div class="flex flex-wrap gap-4 mr-4 justify-center content-center mb-4">
			{#each collections as collection}
				<CollectionCard
					{collection}
					type="link"
					on:link={link}
					bind:linkedCollectionList
					on:unlink={unlink}
					user={null}
				/>
			{/each}
			{#if collections.length === 0}
				<p class="text-center text-lg">{$t('adventures.no_collections_found')}</p>
			{/if}
		</div>
		<button class="btn btn-primary" on:click={close}>{$t('about.close')}</button>
	</div>
</dialog>
