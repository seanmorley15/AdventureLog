<script lang="ts">
	import type { ImageSource } from '$lib/types';
	import { t } from 'svelte-i18n';
	import GoogleIcon from '~icons/mdi/google';
	import WikipediaIcon from '~icons/mdi/wikipedia';
	import ImmichLogo from '$lib/assets/immich.svg';
	import { defaultImageSource } from '$lib/images';

	interface Props {
		source?: ImageSource | null | undefined;
	}

	let { source = 'upload' }: Props = $props();

	let resolvedSource = $derived(defaultImageSource(source));

	const tooltipKeys: Record<Exclude<ImageSource, 'upload'>, string> = {
		google: 'images.source.google',
		wikipedia: 'images.source.wikipedia',
		immich: 'images.source.immich',
		url: 'images.source.url'
	};
</script>

{#if resolvedSource !== 'upload'}
	<div
		class="absolute bottom-1.5 right-1.5 z-10 flex items-center justify-center rounded bg-black/55 p-0.5 shadow-sm pointer-events-none"
		title={$t(tooltipKeys[resolvedSource])}
		aria-label={$t(tooltipKeys[resolvedSource])}
	>
		{#if resolvedSource === 'google'}
			<GoogleIcon class="h-4 w-4 text-white" aria-hidden="true" />
		{:else if resolvedSource === 'wikipedia'}
			<WikipediaIcon class="h-4 w-4 text-white" aria-hidden="true" />
		{:else if resolvedSource === 'immich'}
			<img src={ImmichLogo} alt="" class="h-4 w-4" aria-hidden="true" />
		{:else}
			<span class="px-1 text-[9px] font-semibold uppercase tracking-wide text-white">URL</span>
		{/if}
	</div>
{/if}
