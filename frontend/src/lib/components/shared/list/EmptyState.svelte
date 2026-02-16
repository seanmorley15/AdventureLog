<script lang="ts">
	/**
	 * EmptyState - Empty state display for list pages
	 */
	import { createEventDispatcher } from 'svelte';
	import Plus from '~icons/mdi/plus';

	export let icon: any; // Svelte component
	export let title: string;
	export let message: string;
	export let buttonText: string;

	const dispatch = createEventDispatcher<{ create: void }>();
</script>

<div class="flex flex-col items-center justify-center py-16">
	<div class="p-6 bg-base-200/50 rounded-2xl mb-6">
		<svelte:component this={icon} class="w-16 h-16 text-base-content/30" />
	</div>
	<h3 class="text-xl font-semibold text-base-content/70 mb-2">
		{title}
	</h3>
	<p class="text-base-content/50 text-center max-w-md">
		{message}
	</p>
	<button class="btn btn-primary btn-wide mt-6 gap-2" on:click={() => dispatch('create')}>
		<Plus class="w-5 h-5" />
		{buttonText}
	</button>
</div>
