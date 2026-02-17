<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { t } from 'svelte-i18n';

	const dispatch = createEventDispatcher<{ change: string }>();

	export let types: string;
	export let typeOptions: { value: string; label: string; icon: string }[];
	export let title: string = '';
	export let icon: any = null;
	export let collapsed: boolean = false;

	let types_arr: string[] = [];

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
		{title || $t('adventures.filter_by_type')}
		{#if types_arr.length > 0}
			<span class="badge badge-primary badge-sm">{types_arr.length}</span>
		{/if}
	</div>
	<div class="collapse-content !pb-2">
		<div class="space-y-0">
			{#each typeOptions as type}
				<label class="flex items-center gap-2 cursor-pointer py-0.5">
					<input
						type="checkbox"
						class="checkbox checkbox-primary checkbox-sm"
						value={type.value}
						on:change={() => toggleSelect(type.value)}
						checked={types_arr.includes(type.value)}
					/>
					<span class="flex items-center gap-1">
						<span>{type.icon}</span>
						{type.label}
					</span>
				</label>
			{/each}
			{#if types_arr.length > 0}
				<button class="btn btn-ghost btn-xs mt-1" on:click={clearTypes}>
					{$t('adventures.clear')}
				</button>
			{/if}
		</div>
	</div>
</div>
