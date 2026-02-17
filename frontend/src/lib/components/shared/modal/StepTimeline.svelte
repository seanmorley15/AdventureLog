<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { ModalStep } from './types';

	export let steps: ModalStep[] = [];
	export let entityId: string = '';

	const dispatch = createEventDispatcher<{
		stepClick: { index: number };
	}>();

	function handleStepClick(index: number) {
		const step = steps[index];
		if (step.requires_id && !entityId) return;
		dispatch('stepClick', { index });
	}
</script>

<ul class="timeline timeline-vertical timeline-compact sm:timeline-horizontal sm:timeline-normal">
	{#each steps as step, index}
		<li>
			{#if index > 0}
				<hr class="bg-base-300" />
			{/if}
			<div class="timeline-middle">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="h-4 w-4 sm:h-5 sm:w-5 {step.selected ? 'text-primary' : 'text-base-content/40'}"
				>
					<path
						fill-rule="evenodd"
						d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-0.089l4-5-5z"
						clip-rule="evenodd"
					/>
				</svg>
			</div>
			<button
				class="timeline-end timeline-box text-xs sm:text-sm px-2 py-1 sm:px-3 sm:py-2 {step.selected
					? 'bg-primary text-primary-content'
					: 'bg-base-200'} {step.requires_id && !entityId
					? 'opacity-50 cursor-not-allowed'
					: 'hover:bg-primary/80 cursor-pointer'} transition-colors"
				on:click={() => handleStepClick(index)}
				disabled={step.requires_id && !entityId}
			>
				<span class="hidden sm:inline">{step.name}</span>
				<span class="sm:hidden">{step.name.substring(0, 8)}{step.name.length > 8 ? '...' : ''}</span
				>
			</button>
			{#if index < steps.length - 1}
				<hr class="bg-base-300" />
			{/if}
		</li>
	{/each}
</ul>
