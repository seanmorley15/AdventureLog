<script lang="ts">
	import type { Category } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	let modal: HTMLDialogElement;
	import { t } from 'svelte-i18n';

	export let categories: Category[] = [];

	let category_to_edit: Category | null = null;

	onMount(async () => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}
		let category_fetch = await fetch('/api/categories/categories');
		categories = await category_fetch.json();
		// remove the general category if it exists
		categories = categories.filter((c) => c.name !== 'general');
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
			}
		};
	}
</script>

<dialog id="my_modal_1" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<div class="modal-box" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<h3 class="font-bold text-lg">Manage Categories</h3>

		{#each categories as category}
			<div class="flex justify-between items-center mt-2">
				<span>{category.display_name} {category.icon}</span>
				<div class="flex space-x-2">
					<button on:click={() => (category_to_edit = category)} class="btn btn-primary btn-sm"
						>Edit</button
					>
					<button on:click={removeCategory(category)} class="btn btn-warning btn-sm">Remove</button>
				</div>
			</div>
		{/each}
		{#if categories.length === 0}
			<p>No categories found.</p>
		{/if}

		{#if category_to_edit}
			<input
				type="text"
				placeholder="Name"
				bind:value={category_to_edit.display_name}
				class="input input-bordered w-full max-w-xs"
			/>
			<input
				type="text"
				placeholder="Icon"
				bind:value={category_to_edit.icon}
				class="input input-bordered w-full max-w-xs"
			/>
			<button class="btn btn-primary" on:click={saveCategory}>Save</button>
		{/if}

		<button class="btn btn-primary mt-4" on:click={close}>{$t('about.close')}</button>
	</div>
</dialog>
