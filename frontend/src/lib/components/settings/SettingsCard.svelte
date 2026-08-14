<script lang="ts">
	interface Props {
		padding?: string;
		className?: string;
		id?: string | undefined;
		children?: import('svelte').Snippet;
	}

	let {
		padding = 'p-8',
		className = '',
		id = undefined,
		children
	}: Props = $props();
</script>

<div {id} class="bg-base-100 rounded-2xl shadow-xl {padding} {className}">
	{@render children?.()}
</div>
