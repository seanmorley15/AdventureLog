<script lang="ts">
	import type { ImageSource } from '$lib/types';
	import ImageSourceBadge from './ImageSourceBadge.svelte';
	import { defaultImageSource } from '$lib/images';

	export let source: ImageSource | null | undefined = 'upload';
	export let className = '';
	export let showSourceBadge = false;

	$: resolvedSource = defaultImageSource(source);
</script>

<div class={`relative ${className}`}>
	<slot />
	{#if showSourceBadge}
		<ImageSourceBadge source={resolvedSource} />
	{/if}
	<slot name="overlays" />
</div>
