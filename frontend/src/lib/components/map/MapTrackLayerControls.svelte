<script lang="ts">
	import { t } from 'svelte-i18n';
	import RunFastIcon from '~icons/mdi/run-fast';
	import HikingIcon from '~icons/mdi/hiking';
	import CameraIcon from '~icons/mdi/camera';

	export let showActivities = true;
	export let showTrails = true;
	export let showImagePins = true;
	export let hasActivities = false;
	export let hasTrails = false;
	export let hasImagePins = false;
	/** When true, render inline (no absolute positioning) for use inside a parent toolbar. */
	export let embedded = false;

	const btnBase =
		'btn btn-sm btn-square min-h-8 h-8 w-8 bg-transparent hover:bg-base-200/80 border-0 shadow-none';

	function layerBtnClass(
		show: boolean,
		position: 'first' | 'middle' | 'last' | 'only',
		activeClass: string
	) {
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

	$: layerCount = Number(hasActivities) + Number(hasTrails) + Number(hasImagePins);
	$: activityPosition = !hasActivities
		? 'only'
		: layerCount === 1
			? 'only'
			: !hasTrails && !hasImagePins
				? 'only'
				: 'first';
	$: trailPosition = !hasTrails
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
	$: imagePosition = !hasImagePins ? 'only' : layerCount === 1 ? 'only' : 'last';
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
					on:click={() => (showActivities = !showActivities)}
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
					on:click={() => (showTrails = !showTrails)}
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
					on:click={() => (showImagePins = !showImagePins)}
				>
					<CameraIcon class="w-5 h-5" />
				</button>
			{/if}
		</div>
	</div>
{/if}
