<script lang="ts">
	import type { Category } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	let modal: HTMLDialogElement;
	import { t } from 'svelte-i18n';

	export let categories: Category[] = [];

	let category_to_edit: Category | null = null;

	let is_changed: boolean = false;

	let has_loaded: boolean = false;

	onMount(async () => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}
		let category_fetch = await fetch('/api/categories/categories');
		categories = await category_fetch.json();
		has_loaded = true;
		// remove the general category if it exists
		// categories = categories.filter((c) => c.name !== 'general');
	});

	async function saveCategory() {
		if (category_to_edit) {
			let edit_fetch = await fetch(`/api/categories/${category_to_edit.id}`, {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(category_to_edit)
			});
			if (edit_fetch.ok) {
				category_to_edit = null;
				let the_category = (await edit_fetch.json()) as Category;
				categories = categories.map((c) => {
					if (c.id === the_category.id) {
						return the_category;
					}
					return c;
				});
				is_changed = true;
			}
		}
	}

	function close() {
		dispatch('close');
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			dispatch('close');
		}
	}

	function removeCategory(category: Category) {
		return async () => {
			let response = await fetch(`/api/categories/${category.id}`, {
				method: 'DELETE'
			});
			if (response.ok) {
				categories = categories.filter((c) => c.id !== category.id);
				is_changed = true;
			}
		};
	}
</script>

<dialog id="my_modal_1" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<div class="modal-box" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<h3 class="font-bold text-lg">{$t('categories.manage_categories')}</h3>

		{#if has_loaded}
			{#each categories as category}
				<div class="flex justify-between items-center mt-2">
					<span>{category.display_name} {category.icon}</span>
					<div class="flex space-x-2">
						<button on:click={() => (category_to_edit = category)} class="btn btn-primary btn-sm"
							>Edit</button
						>
						{#if category.name != 'general'}
							<button on:click={removeCategory(category)} class="btn btn-warning btn-sm"
								>{$t('adventures.remove')}</button
							>
						{:else}
							<button class="btn btn-warning btn-sm btn-disabled">{$t('adventures.remove')}</button>
						{/if}
					</div>
				</div>
			{/each}
			{#if categories.length === 0}
				<p>{$t('categories.no_categories_found')}</p>
			{/if}
		{:else}
			<div class="flex items-center justify-center">
				<span class="loading loading-spinner loading-lg m-4"></span>
			</div>
		{/if}

		{#if category_to_edit}
			<h2 class="text-center text-xl font-semibold mt-2 mb-2">{$t('categories.edit_category')}</h2>
			<div class="flex flex-row space-x-2 form-control">
				<input
					type="text"
					placeholder={$t('adventures.name')}
					bind:value={category_to_edit.display_name}
					class="input input-bordered w-full max-w-xs"
				/>

				<input
					type="text"
					placeholder={$t('categories.icon')}
					bind:value={category_to_edit.icon}
					class="input input-bordered w-full max-w-xs"
				/>
			</div>
			<button class="btn btn-primary" on:click={saveCategory}>{$t('notes.save')}</button>
		{/if}

		<button class="btn btn-primary mt-4" on:click={close}>{$t('about.close')}</button>

		{#if is_changed}
			<div role="alert" class="alert alert-info mt-6">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					class="h-6 w-6 shrink-0 stroke-current"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
					></path>
				</svg>
				<span>{$t('categories.update_after_refresh')}</span>
			</div>
		{/if}
	</div>
</dialog>
