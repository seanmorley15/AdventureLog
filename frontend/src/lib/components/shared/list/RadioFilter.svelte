<script lang="ts">
	/**
	 * RadioFilter - Generic radio button filter card (collapsible)
	 * Used for visited, visibility, ownership filters
	 */
	import { createEventDispatcher } from 'svelte';

	export let title: string;
	export let icon: any; // Svelte component
	export let value: string = 'all';
	export let options: { value: string; label: string }[] = [];
	export let name: string = 'filter'; // Unique name for radio group
	export let collapsed: boolean = false;

	const dispatch = createEventDispatcher<{ change: string }>();

	function handleChange(newValue: string) {
		value = newValue;
		dispatch('change', newValue);
	}

	$: activeLabel = options.find((o) => o.value === value)?.label || '';
	$: isFiltered = value !== 'all';
</script>

<div class="collapse collapse-arrow bg-base-200/50 rounded-box">
	<input type="checkbox" checked={!collapsed} />
	<div class="collapse-title font-medium flex items-center gap-2 py-2 min-h-0">
		<svelte:component this={icon} class="w-5 h-5" />
		{title}
		{#if isFiltered}
			<span class="badge badge-primary badge-sm">{activeLabel}</span>
		{/if}
	</div>
	<div class="collapse-content !pb-2">
		<div class="space-y-0">
			{#each options as option}
				<label class="flex items-center gap-2 cursor-pointer py-0.5">
					<input
						type="radio"
						name={name}
						class="radio radio-primary radio-sm"
						checked={value === option.value}
						on:change={() => handleChange(option.value)}
					/>
					<span>{option.label}</span>
				</label>
			{/each}
		</div>
	</div>
</div>
