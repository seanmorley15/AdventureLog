<script lang="ts">
	import type { Category } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	import { onMount } from 'svelte';
	import { t } from 'svelte-i18n';

	let types_arr: string[] = [];
	export let types: string;
	let adventure_types: Category[] = [];
	const dispatch = createEventDispatcher<{ change: { types: string } }>();

	$: sortedAdventureTypes = [...adventure_types].sort((a, b) => {
		const usageDiff = (b.num_locations || 0) - (a.num_locations || 0);
		if (usageDiff !== 0) return usageDiff;
		return (a.display_name || '').localeCompare(b.display_name || '');
	});

	onMount(async () => {
		try {
			const categoryFetch = await fetch('/api/categories');
			const categoryData = await categoryFetch.json();
			adventure_types = Array.isArray(categoryData) ? categoryData : [];
		} catch (err) {
			console.error('Failed to load categories:', err);
			adventure_types = [];
		}
	});

	$: {
		types_arr = types ? types.split(',').filter((item) => item !== '') : [];
	}

	function clearTypes() {
		types_arr = [];
		dispatch('change', { types: '' });
	}

	function toggleSelect(type: string) {
		if (types_arr.includes(type)) {
			types_arr = types_arr.filter((item) => item !== type);
		} else {
			types_arr = [...types_arr, type];
		}
		dispatch('change', { types: types_arr.join(',') });
	}
</script>

<div>
	{#if types_arr.length > 0}
		<div class="flex justify-end mb-2">
			<button type="button" class="btn btn-ghost btn-xs h-auto min-h-0 px-2" on:click={clearTypes}>
				{$t('adventures.clear')}
			</button>
		</div>
	{/if}

	{#if adventure_types.length === 0}
		<p class="text-sm text-base-content/60 text-center py-2">
			{$t('categories.no_categories_found')}
		</p>
	{:else}
		<div class="max-h-40 overflow-y-auto space-y-1 -mx-1 px-1">
			{#each sortedAdventureTypes as type (type.id)}
				<label class="label cursor-pointer justify-start gap-3 py-1 min-h-0">
					<input
						type="checkbox"
						class="checkbox checkbox-primary checkbox-sm"
						value={type.name}
						on:change={() => toggleSelect(type.name)}
						checked={types_arr.includes(type.name)}
					/>
					<span class="label-text leading-tight">
						{type.icon}
						{type.display_name}
						<span class="text-base-content/50">({type.num_locations})</span>
					</span>
				</label>
			{/each}
		</div>
	{/if}
</div>
