<script lang="ts">
	import type { Category } from '$lib/types';
	import { createEventDispatcher, onMount } from 'svelte';
	import { t } from 'svelte-i18n';

	let types_arr: string[] = [];
	export let types: string;
	let adventure_types: Category[] = [];
	let isOpen = false;

	const dispatch = createEventDispatcher();

	onMount(async () => {
		let categoryFetch = await fetch('/api/categories');
		let categoryData = await categoryFetch.json();
		adventure_types = categoryData;
		types_arr = types ? types.split(',').filter((item) => item !== '') : [];
	});

	function clearTypes() {
		types = '';
		types_arr = [];
		dispatch('change');
	}

	function toggleSelect(type: string) {
		if (types_arr.indexOf(type) > -1) {
			types_arr = types_arr.filter((item) => item !== type);
		} else {
			types_arr = [...types_arr, type];
		}
		types_arr = types_arr.filter((item) => item !== '');
		types = types_arr.join(',');
		dispatch('change');
	}
</script>

<div class="mb-4">
	<button
		type="button"
		class="flex items-center justify-between w-full cursor-pointer p-4 bg-base-300 rounded-t-lg {!isOpen
			? 'rounded-b-lg'
			: ''}"
		on:click={() => (isOpen = !isOpen)}
	>
		<span class="text-xl font-medium">{$t('adventures.category_filter')}</span>
		<span class="text-xl transition-transform duration-200 {isOpen ? 'rotate-45' : ''}">+</span>
	</button>

	{#if isOpen}
		<div class="bg-base-300 px-4 pb-4 rounded-b-lg">
			<button
				type="button"
				class="btn btn-sm btn-neutral-300 w-full mb-2"
				on:click={clearTypes}
			>
				{$t('adventures.clear')}
			</button>

			<ul>
				{#each adventure_types as type}
					<li class="mb-1">
						<label class="cursor-pointer flex items-center gap-2">
							<input
								type="checkbox"
								class="checkbox"
								value={type.name}
								on:change={() => toggleSelect(type.name)}
								checked={types_arr.indexOf(type.name) > -1}
							/>
							<span>
								{type.display_name}
								{type.icon} ({type.num_locations})
							</span>
						</label>
					</li>
				{/each}
			</ul>
		</div>
	{/if}
</div>
