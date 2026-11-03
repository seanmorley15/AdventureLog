<script lang="ts">
	import { beforeNavigate, preloadData } from '$app/navigation';
	import { fly, fade } from 'svelte/transition';
	import { t } from 'svelte-i18n';
	import {
		closeLocationDrawer,
		locationDrawer,
		openLocationHref
	} from '#lib/location-drawer.svelte.js';
	import Close from '~icons/mdi/close';
	import OpenInNew from '~icons/mdi/open-in-new';

	let target = $derived(locationDrawer.target);

	function loadLocation(id: string, hash: string) {
		return Promise.all([
			preloadData(`/locations/${id}${hash}`),
			import('../../../routes/locations/[id]/+page.svelte')
		]);
	}

	beforeNavigate(() => {
		if (locationDrawer.target) closeLocationDrawer();
	});

	function onKeydown(event: KeyboardEvent) {
		if (event.key !== 'Escape' || !locationDrawer.target) return;
		if (document.querySelector('dialog[open]')) return;
		event.preventDefault();
		closeLocationDrawer();
	}

	function interceptLocationLink(event: MouseEvent) {
		if (event.defaultPrevented || event.button !== 0) return;
		if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

		const eventTarget = event.target;
		if (!(eventTarget instanceof Element)) return;

		const anchor = eventTarget.closest('a');
		if (!anchor) return;
		if (anchor.target === '_blank' || anchor.hasAttribute('download')) return;
		if (anchor.dataset.locationDrawer === 'ignore') return;

		const href = anchor.getAttribute('href');
		if (!href || href.startsWith('mailto:') || href.startsWith('tel:')) return;
		if (!openLocationHref(anchor.href)) return;

		event.preventDefault();
		event.stopPropagation();
	}
</script>

<svelte:window onkeydowncapture={onKeydown} onclickcapture={interceptLocationLink} />

{#if target}
	<div class="fixed inset-0 z-[1100]">
		<button
			type="button"
			class="absolute inset-0 bg-black/40"
			aria-label={$t('about.close')}
			onclick={closeLocationDrawer}
			transition:fade={{ duration: 150 }}
		></button>

		<div
			class="absolute inset-y-0 right-0 flex h-full w-full shadow-2xl md:w-[min(40rem,92vw)]"
			role="dialog"
			aria-modal="true"
			aria-label={$t('map.view_details')}
			transition:fly={{ x: 420, duration: 220 }}
		>
			<div
				class="location-drawer relative h-full w-full overflow-y-auto overscroll-contain bg-base-100"
			>
				<div
					class="sticky top-0 z-30 flex items-center justify-end gap-2 border-b border-base-300 bg-base-100/90 px-3 py-2 backdrop-blur"
				>
					<a
						class="btn btn-ghost btn-sm gap-1"
						href="/locations/{target.id}{target.hash}"
						data-location-drawer="ignore"
					>
						<OpenInNew class="h-4 w-4" />
						{$t('map.view_details')}
					</a>
					<button
						type="button"
						class="btn btn-circle btn-ghost btn-sm"
						aria-label={$t('about.close')}
						onclick={closeLocationDrawer}
					>
						<Close class="h-5 w-5" />
					</button>
				</div>

				{#key target.id + target.hash}
					{#await loadLocation(target.id, target.hash)}
						<div class="flex min-h-[50vh] items-center justify-center">
							<span class="loading loading-spinner h-16 w-16 text-primary"></span>
						</div>
					{:then [result, pageModule]}
						{#if result.type === 'loaded'}
							{@const LocationPage = pageModule.default}
							<LocationPage data={result.data} embedded scrollHash={target.hash} />
						{:else}
							<div class="p-8 text-center">
								<p class="text-lg">{$t('adventures.location_not_found')}</p>
							</div>
						{/if}
					{:catch}
						<div class="p-8 text-center">
							<p class="text-lg">{$t('adventures.location_not_found')}</p>
						</div>
					{/await}
				{/key}
			</div>
		</div>
	</div>
{/if}

<style>
	.location-drawer {
		transform: translateZ(0);
	}

	.location-drawer :global(.hero) {
		min-height: 12rem;
	}

	.location-drawer :global(h1) {
		font-size: 2.25rem;
		line-height: 1.15;
	}

	.location-drawer :global(.min-h-screen) {
		min-height: 24rem;
	}
</style>
