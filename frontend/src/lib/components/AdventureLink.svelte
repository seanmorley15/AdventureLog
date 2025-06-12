<script lang="ts">
	import type { Adventure, User } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { t } from 'svelte-i18n';
	import { onMount } from 'svelte';
	import AdventureCard from './AdventureCard.svelte';
	let modal: HTMLDialogElement;

	let adventures: Adventure[] = [];

	let isLoading: boolean = true;

	export let user: User | null;
	export let collectionId: string;

	onMount(async () => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}
		let res = await fetch(`/api/adventures/all/?include_collections=true`, {
			method: 'GET'
		});

		const newAdventures = await res.json();

		// Filter out adventures that are already linked to the collections
		// basically for each adventure, check if collections array contains the id of the current collection
		if (collectionId) {
			adventures = newAdventures.filter((adventure: Adventure) => {
				// adventure.collections is an array of ids, collectionId is a single id
				return !(adventure.collections ?? []).includes(collectionId);
			});
		} else {
			adventures = newAdventures;
		}

		// No need to reassign adventures to newAdventures here, keep the filtered result
		isLoading = false;
	});

	function close() {
		dispatch('close');
	}

	function add(event: CustomEvent<Adventure>) {
		adventures = adventures.filter((a) => a.id !== event.detail.id);
		dispatch('add', event.detail);
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
		<h1 class="text-center font-bold text-4xl mb-6">{$t('adventures.my_adventures')}</h1>
		{#if isLoading}
			<div class="flex justify-center items-center w-full mt-16">
				<span class="loading loading-spinner w-24 h-24"></span>
			</div>
		{/if}
		<div class="flex flex-wrap gap-4 mr-4 justify-center content-center">
			{#each adventures as adventure}
				<AdventureCard {user} type="link" {adventure} on:link={add} />
			{/each}
			{#if adventures.length === 0 && !isLoading}
				<p class="text-center text-lg">
					{$t('adventures.no_linkable_adventures')}
				</p>
			{/if}
		</div>
		<button class="btn btn-primary" on:click={close}>{$t('about.close')}</button>
	</div>
</dialog>
