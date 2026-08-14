<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import { addToast } from '$lib/toasts';
	import MapStyleSelector from '$lib/components/map/MapStyleSelector.svelte';
	import PlusIcon from '~icons/mdi/plus';
	import MinusIcon from '~icons/mdi/minus';
	import CrosshairsGpsIcon from '~icons/mdi/crosshairs-gps';
	import FullscreenIcon from '~icons/mdi/fullscreen';
	import FullscreenExitIcon from '~icons/mdi/fullscreen-exit';

	
	interface Props {
		map?: any;
		basemapType?: string;
		showBasemapSelector?: boolean;
		fullscreenTarget?: HTMLElement | null;
		/** When true, render inline (no absolute positioning) for use inside a parent toolbar. */
		embedded?: boolean;
	}

	let {
		map = undefined,
		basemapType = $bindable('default'),
		showBasemapSelector = true,
		fullscreenTarget = null,
		embedded = false
	}: Props = $props();

	let isFullscreen = $state(false);
	let locating = $state(false);

	const btnClass =
		'btn btn-sm btn-square min-h-8 h-8 w-8 bg-transparent hover:bg-base-200/80 border-0 rounded-none shadow-none';

	function getFullscreenElement(): HTMLElement | null {
		if (fullscreenTarget) return fullscreenTarget;
		const container = map?.getContainer?.();
		if (!container) return null;
		return (
			container.closest('.fullmap-root') ??
			container.closest('.relative') ??
			container.parentElement ??
			container
		);
	}

	function zoomIn() {
		map?.zoomIn?.({ duration: 250 });
	}

	function zoomOut() {
		map?.zoomOut?.({ duration: 250 });
	}

	function locateUser() {
		if (!map) return;
		if (!navigator.geolocation) {
			addToast('warning', $t('map.geolocation_unavailable'));
			return;
		}

		locating = true;
		navigator.geolocation.getCurrentPosition(
			(position) => {
				map.flyTo({
					center: [position.coords.longitude, position.coords.latitude],
					zoom: Math.max(map.getZoom(), 14),
					duration: 800
				});
				locating = false;
			},
			() => {
				addToast('warning', $t('map.geolocation_denied'));
				locating = false;
			},
			{ enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
		);
	}

	async function toggleFullscreen() {
		const target = getFullscreenElement();
		if (!target) return;

		try {
			if (!document.fullscreenElement) {
				await target.requestFullscreen();
			} else {
				await document.exitFullscreen();
			}
		} catch {
			addToast('warning', $t('map.fullscreen_failed'));
		}
	}

	function handleFullscreenChange() {
		isFullscreen = Boolean(document.fullscreenElement);
		requestAnimationFrame(() => {
			map?.resize?.();
		});
	}

	onMount(() => {
		document.addEventListener('fullscreenchange', handleFullscreenChange);
	});

	onDestroy(() => {
		document.removeEventListener('fullscreenchange', handleFullscreenChange);
	});
</script>

<div
	class:pointer-events-none={!embedded}
	class:absolute={!embedded}
	class:top-3={!embedded}
	class:right-3={!embedded}
	class:z-20={!embedded}
	class="flex items-center pointer-events-auto"
	role="toolbar"
	aria-label={$t('map.map_controls')}
>
	<div
		class="flex items-center rounded-xl border border-base-300 shadow-md bg-base-100/90 backdrop-blur-lg divide-x divide-base-300/80 overflow-visible"
	>
		{#if showBasemapSelector}
			<div class="shrink-0 relative z-[60]">
				<MapStyleSelector bind:basemapType dropdownClass="dropdown dropdown-end dropdown-bottom" />
			</div>
		{/if}

		<button type="button" class={btnClass} onclick={zoomIn} aria-label={$t('map.zoom_in')}>
			<PlusIcon class="w-5 h-5" />
		</button>
		<button type="button" class={btnClass} onclick={zoomOut} aria-label={$t('map.zoom_out')}>
			<MinusIcon class="w-5 h-5" />
		</button>
		<button
			type="button"
			class={btnClass}
			class:loading={locating}
			disabled={locating}
			onclick={locateUser}
			aria-label={$t('map.locate_me')}
		>
			<CrosshairsGpsIcon class="w-5 h-5" />
		</button>
		<button
			type="button"
			class={btnClass}
			onclick={toggleFullscreen}
			aria-label={isFullscreen ? $t('map.exit_fullscreen') : $t('map.enter_fullscreen')}
		>
			{#if isFullscreen}
				<FullscreenExitIcon class="w-5 h-5" />
			{:else}
				<FullscreenIcon class="w-5 h-5" />
			{/if}
		</button>
	</div>
</div>
