<script lang="ts">
	import type { Category } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	import { onMount } from 'svelte';
	import { t } from 'svelte-i18n';

	let types_arr: string[] = [];
	export let types: string;
	let adventure_types: Category[] = [];
	let isOpen = false;
	const dispatch = createEventDispatcher<{ change: { types: string } }>();

	onMount(async () => {
		let categoryFetch = await fetch('/api/categories');
		let categoryData = await categoryFetch.json();
		adventure_types = categoryData;
	});

	$: {
		types_arr = types ? types.split(',').filter((item) => item !== '') : [];
	}

	function clearTypes() {
		types = '';
		types_arr = [];
		dispatch('change', { types });
	}

	function toggleSelect(type: string) {
		if (types_arr.indexOf(type) > -1) {
			types_arr = types_arr.filter((item) => item !== type);
		} else {
			types_arr.push(type);
		}
		types_arr = types_arr.filter((item) => item !== '');
		// turn types_arr into a comma seperated list with no spaces
		types = types_arr.join(',');
		dispatch('change', { types });
	}
</script>

<div class="mb-4 rounded-lg bg-base-300">
	<button
		type="button"
		class="w-full text-left text-xl font-medium p-4"
		on:click={() => (isOpen = !isOpen)}
	>
		{$t('adventures.category_filter')}
	</button>

	{#if isOpen}
		<div class="px-4 pb-4">
			<button type="button" class="btn btn-sm btn-neutral-300 w-full mb-2" on:click={clearTypes}>
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
								checked={types_arr.includes(type.name)}
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
