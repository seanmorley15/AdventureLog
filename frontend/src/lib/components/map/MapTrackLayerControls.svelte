<script lang="ts">
	import { run } from 'svelte/legacy';

	import { t } from 'svelte-i18n';
	import RunFastIcon from '~icons/mdi/run-fast';
	import HikingIcon from '~icons/mdi/hiking';
	import CameraIcon from '~icons/mdi/camera';

	
	interface Props {
		showActivities?: boolean;
		showTrails?: boolean;
		showImagePins?: boolean;
		hasActivities?: boolean;
		hasTrails?: boolean;
		hasImagePins?: boolean;
		/** When true, render inline (no absolute positioning) for use inside a parent toolbar. */
		embedded?: boolean;
	}

	let {
		showActivities = $bindable(true),
		showTrails = $bindable(true),
		showImagePins = $bindable(true),
		hasActivities = false,
		hasTrails = false,
		hasImagePins = false,
		embedded = false
	}: Props = $props();

	const btnBase =
		'btn btn-sm btn-square min-h-8 h-8 w-8 bg-transparent hover:bg-base-200/80 border-0 shadow-none';

	type LayerPosition = 'first' | 'middle' | 'last' | 'only';

	function layerBtnClass(show: boolean, position: LayerPosition, activeClass: string) {
		const rounded =
			position === 'only'
				? 'rounded-xl'
				: position === 'first'
					? 'rounded-l-xl rounded-r-none'
					: position === 'last'
						? 'rounded-r-xl rounded-l-none'
						: 'rounded-none';
		const state = show ? activeClass : 'opacity-45';
		return `${btnBase} ${rounded} ${state}`;
	}

	let layerCount = $derived(Number(hasActivities) + Number(hasTrails) + Number(hasImagePins));
	let activityPosition: LayerPosition = $state('only');
	let trailPosition: LayerPosition = $state('only');
	let imagePosition: LayerPosition = $state('only');
	run(() => {
		activityPosition = !hasActivities
			? 'only'
			: layerCount === 1
				? 'only'
				: !hasTrails && !hasImagePins
					? 'only'
					: 'first';
	});
	run(() => {
		trailPosition = !hasTrails
			? 'only'
			: layerCount === 1
				? 'only'
				: !hasImagePins
					? hasActivities
						? 'last'
						: 'only'
					: hasActivities
						? 'middle'
						: 'first';
	});
	run(() => {
		imagePosition = !hasImagePins ? 'only' : layerCount === 1 ? 'only' : 'last';
	});
</script>

{#if hasActivities || hasTrails || hasImagePins}
	<div
		class:pointer-events-none={!embedded}
		class:absolute={!embedded}
		class:top-3={!embedded}
		class:left-3={!embedded}
		class:z-20={!embedded}
		class="flex items-center pointer-events-auto"
		role="toolbar"
		aria-label={$t('map.track_layers')}
	>
		<div
			class="flex items-center rounded-xl border border-base-300 shadow-md bg-base-100/90 backdrop-blur-lg divide-x divide-base-300/80 overflow-hidden"
		>
			{#if hasActivities}
				<button
					type="button"
					class={layerBtnClass(showActivities, activityPosition, 'bg-primary/15 text-primary')}
					aria-pressed={showActivities}
					aria-label={showActivities ? $t('map.hide_activities') : $t('map.show_activities')}
					title={showActivities ? $t('map.hide_activities') : $t('map.show_activities')}
					onclick={() => (showActivities = !showActivities)}
				>
					<RunFastIcon class="w-5 h-5" />
				</button>
			{/if}
			{#if hasTrails}
				<button
					type="button"
					class={layerBtnClass(showTrails, trailPosition, 'bg-[#a855f7]/15 text-[#a855f7]')}
					aria-pressed={showTrails}
					aria-label={showTrails ? $t('map.hide_trails') : $t('map.show_trails')}
					title={showTrails ? $t('map.hide_trails') : $t('map.show_trails')}
					onclick={() => (showTrails = !showTrails)}
				>
					<HikingIcon class="w-5 h-5" />
				</button>
			{/if}
			{#if hasImagePins}
				<button
					type="button"
					class={layerBtnClass(showImagePins, imagePosition, 'bg-rose-500/15 text-rose-500')}
					aria-pressed={showImagePins}
					aria-label={showImagePins ? $t('map.hide_image_pins') : $t('map.show_image_pins')}
					title={showImagePins ? $t('map.hide_image_pins') : $t('map.show_image_pins')}
					onclick={() => (showImagePins = !showImagePins)}
				>
					<CameraIcon class="w-5 h-5" />
				</button>
			{/if}
		</div>
	</div>
{/if}
