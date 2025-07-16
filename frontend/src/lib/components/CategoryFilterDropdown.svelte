<script lang="ts">
	import type { Category } from '$lib/types';
	import { onMount } from 'svelte';
	import { t } from 'svelte-i18n';

	let types_arr: string[] = [];
	export let types: string;
	let adventure_types: Category[] = [];

	onMount(async () => {
		let categoryFetch = await fetch('/api/categories');
		let categoryData = await categoryFetch.json();
		adventure_types = categoryData;
		console.log(categoryData);
		types_arr = types.split(',');
	});

	function clearTypes() {
		types = '';
		types_arr = [];
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

		console.log(types);
		console.log(types_arr);
	}
</script>

<div class="collapse collapse-plus mb-4">
	<input type="checkbox" />

	<div class="collapse-title text-xl bg-base-300 font-medium">
		{$t('adventures.category_filter')}
	</div>

	<div class="collapse-content bg-base-300">
		<button class="btn btn-sm btn-neutral-300 w-full mb-2" on:click={clearTypes}>
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
							checked={types.indexOf(type.name) > -1}
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
</div>
