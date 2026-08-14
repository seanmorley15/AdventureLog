<script lang="ts">
	interface Props {
		title: string;
		description?: string;
		showDivider?: boolean;
		children?: import('svelte').Snippet;
	}

	let {
		title,
		description = '',
		showDivider = true,
		children
	}: Props = $props();
</script>

{#if showDivider}
	<div class="divider my-8">{title}</div>
{:else}
	<div class="mb-6">
		<h3 class="text-lg font-semibold">{title}</h3>
		{#if description}
			<p class="text-sm text-base-content/70 mt-1">{description}</p>
		{/if}
	</div>
{/if}

{@render children?.()}
