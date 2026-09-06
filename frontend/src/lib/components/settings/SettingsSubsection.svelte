<script lang="ts">
	interface Props {
		title: string;
		description?: string;
		showDivider?: boolean;
		children?: import('svelte').Snippet;
	}

	let { title, description = '', showDivider = true, children }: Props = $props();
</script>

<div class={showDivider ? 'mt-8 pt-8 mb-6 border-t border-base-300' : 'mb-6'}>
	<h3 class="text-lg font-bold text-base-content">{title}</h3>
	{#if description}
		<p class="text-sm text-base-content/80 mt-1">{description}</p>
	{/if}
</div>

{@render children?.()}
