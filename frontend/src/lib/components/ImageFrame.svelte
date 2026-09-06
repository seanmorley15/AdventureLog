<script lang="ts">
	import type { ImageSource } from '$lib/types';
	import ImageSourceBadge from './ImageSourceBadge.svelte';
	import { defaultImageSource } from '$lib/images';

	interface Props {
		source?: ImageSource | null | undefined;
		className?: string;
		showSourceBadge?: boolean;
		children?: import('svelte').Snippet;
		overlays?: import('svelte').Snippet;
	}

	let {
		source = 'upload',
		className = '',
		showSourceBadge = false,
		children,
		overlays
	}: Props = $props();

	let resolvedSource = $derived(defaultImageSource(source));
</script>

<div class={`relative ${className}`}>
	{@render children?.()}
	{#if showSourceBadge}
		<ImageSourceBadge source={resolvedSource} />
	{/if}
	{@render overlays?.()}
</div>
