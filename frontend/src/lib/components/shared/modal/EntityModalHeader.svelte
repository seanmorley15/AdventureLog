<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { StepTimeline, type ModalStep, navigateToStep } from './index';

	export let icon: any = null; // Svelte component for icon
	export let title: string;
	export let subtitle: string;
	export let steps: ModalStep[];
	export let entityId: string;

	const dispatch = createEventDispatcher();

	function handleStepClick(e: CustomEvent<{ index: number }>) {
		dispatch('stepClick', e.detail);
	}

	function handleClose() {
		dispatch('close');
	}
</script>

<div
	class="top-0 z-10 bg-base-100/90 backdrop-blur-lg border-b border-base-300 -mx-6 -mt-6 px-6 py-4 mb-6"
>
	<div class="flex items-center justify-between">
		<div class="flex items-center gap-3">
			<div class="p-2 bg-primary/10 rounded-xl">
				{#if icon}
					<svelte:component this={icon} class="w-6 h-6 text-primary" />
				{:else}
					<slot name="icon" />
				{/if}
			</div>
			<div>
				<h1 class="text-3xl font-bold text-primary bg-clip-text">
					{title}
				</h1>
				<p class="text-sm text-base-content/60">
					{subtitle}
				</p>
			</div>
		</div>

		<StepTimeline
			{steps}
			{entityId}
			on:stepClick={handleStepClick}
		/>

		<!-- Close Button -->
		<button class="btn btn-ghost btn-square" on:click={handleClose}>
			<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M6 18L18 6M6 6l12 12"
				/>
			</svg>
		</button>
	</div>
</div>
