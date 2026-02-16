<script lang="ts">
	import type { ComponentType } from 'svelte';

	export let title: string;
	export let icon: ComponentType;
	export let iconColorClass: string = 'text-primary';
	export let iconBgClass: string = 'bg-primary/10';
</script>

<div class="card bg-base-100 border border-base-300 shadow-lg">
	<div class="card-body p-6">
		<div class="flex items-center gap-3 mb-6">
			<div class="p-2 {iconBgClass} rounded-lg">
				<svelte:component this={icon} class="w-5 h-5 {iconColorClass}" />
			</div>
			<h2 class="text-xl font-bold">{title}</h2>
		</div>

		<slot />
	</div>
</div>
