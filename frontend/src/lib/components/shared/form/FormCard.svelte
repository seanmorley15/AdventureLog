<script lang="ts">
	/**
	 * A reusable card container with an optional icon header.
	 * Used in modal forms to group related fields.
	 */

	export let title: string = '';
	export let icon: any = null; // Svelte component for the icon
	export let iconClass: string = 'w-5 h-5 text-primary';
	export let noPadding: boolean = false;
</script>

<div class="card bg-base-200/50 shadow-sm">
	{#if title || icon}
		<div class="card-title px-4 pt-4 pb-2 flex items-center gap-2">
			{#if icon}
				<svelte:component this={icon} class={iconClass} />
			{/if}
			{#if title}
				<span class="text-sm font-semibold">{title}</span>
			{/if}
		</div>
	{/if}
	<div class="card-body {noPadding ? 'p-0' : 'p-4'} {title || icon ? 'pt-2' : ''}">
		<slot />
	</div>
</div>
