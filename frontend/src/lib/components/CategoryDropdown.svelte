<script lang="ts">
	import { onMount } from 'svelte';
	import type { Category } from '$lib/types';
	import { t } from 'svelte-i18n';

	export let categories: Category[] = [];
	let selected_category: Category | null = null;

	export let category_id:
		| {
				id: string;
				name: string;
				display_name: string;
				icon: string;
				user_id: string;
		  }
		| string;
	let isOpen = false;

	function toggleDropdown() {
		isOpen = !isOpen;
	}

	function selectCategory(category: Category) {
		selected_category = category;
		category_id = category.id;
		isOpen = false;
	}

	function removeCategory(categoryName: string) {
		categories = categories.filter((category) => category.name !== categoryName);
		if (selected_category && selected_category.name === categoryName) {
			selected_category = null;
		}
	}

	// Close dropdown when clicking outside
	let dropdownRef: HTMLDivElement;
	onMount(() => {
		if (category_id) {
			// when category_id is passed, it will be the full object not just the id that is why we can use it directly as selected_category
			selected_category = category_id as Category;
		}
		const handleClickOutside = (event: MouseEvent) => {
			if (dropdownRef && !dropdownRef.contains(event.target as Node)) {
				isOpen = false;
			}
		};
		document.addEventListener('click', handleClickOutside);
		return () => {
			document.removeEventListener('click', handleClickOutside);
		};
	});
</script>

<div class="mt-2 relative" bind:this={dropdownRef}>
	<button type="button" class="btn btn-outline w-full text-left" on:click={toggleDropdown}>
		{selected_category
			? selected_category.display_name + ' ' + selected_category.icon
			: 'Select Category'}
	</button>

	{#if isOpen}
		<div class="absolute z-10 w-full mt-1 bg-base-300 rounded shadow-lg p-2 flex flex-wrap gap-2">
			{#each categories as category}
				<div
					class="btn btn-neutral flex items-center space-x-2"
					on:click={() => selectCategory(category)}
				>
					<span>{category.display_name} {category.icon}</span>
					<button
						type="button"
						class="btn btn-xs btn-error"
						on:click|stopPropagation={() => removeCategory(category.name)}
					>
						{$t('adventures.remove')}
					</button>
				</div>
			{/each}
		</div>
	{/if}
</div>
