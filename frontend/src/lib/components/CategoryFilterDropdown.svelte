<script lang="ts">
	import type { Category } from '$lib/types';
	import { createEventDispatcher, onMount } from 'svelte';
	import { t } from 'svelte-i18n';

	const dispatch = createEventDispatcher<{ change: string }>();

	let types_arr: string[] = [];
	export let types: string;
	export let title: string = '';
	export let icon: any = null;
	export let collapsed: boolean = false;
	let adventure_types: Category[] = [];

	onMount(async () => {
		let categoryFetch = await fetch('/api/categories');
		let categoryData = await categoryFetch.json();
		adventure_types = categoryData;
		types_arr = types ? types.split(',').filter((t) => t !== '') : [];
	});

	$: types_arr = types ? types.split(',').filter((t) => t !== '') : [];

	function clearTypes() {
		types = '';
		types_arr = [];
		dispatch('change', types);
	}

	function toggleSelect(type: string) {
		if (types_arr.indexOf(type) > -1) {
			types_arr = types_arr.filter((item) => item !== type);
		} else {
			types_arr = [...types_arr, type];
		}
		types_arr = types_arr.filter((item) => item !== '');
		types = types_arr.join(',');
		dispatch('change', types);
	}
</script>

<div class="collapse collapse-arrow bg-base-200/50 rounded-box">
	<input type="checkbox" checked={!collapsed} />
	<div class="collapse-title font-medium flex items-center gap-2 py-2 min-h-0">
		{#if icon}
			<svelte:component this={icon} class="w-5 h-5" />
		{/if}
		{title || $t('adventures.categories')}
		{#if types_arr.length > 0}
			<span class="badge badge-primary badge-sm">{types_arr.length}</span>
		{/if}
	</div>
	<div class="collapse-content !pb-2">
		<div class="space-y-0">
			{#each adventure_types as type}
				<label class="flex items-center gap-2 cursor-pointer py-0.5">
					<input
						type="checkbox"
						class="checkbox checkbox-primary checkbox-sm"
						value={type.name}
						on:change={() => toggleSelect(type.name)}
						checked={types_arr.includes(type.name)}
					/>
					<span class="flex items-center gap-1">
						<span>{type.icon}</span>
						{type.display_name}
						<span class="text-xs opacity-60">({type.num_locations})</span>
					</span>
				</label>
			{/each}
			{#if types_arr.length > 0}
				<button class="btn btn-ghost btn-xs mt-1" on:click={clearTypes}>
					{$t('adventures.clear')}
				</button>
			{/if}
		</div>
		<slot />
	</div>
</div>
