<script lang="ts">
	import { t } from 'svelte-i18n';
	import RunFastIcon from '~icons/mdi/run-fast';
	import HikingIcon from '~icons/mdi/hiking';

	export let showActivities = true;
	export let showTrails = true;
	export let hasActivities = false;
	export let hasTrails = false;
	/** When true, render inline (no absolute positioning) for use inside a parent toolbar. */
	export let embedded = false;

	const btnBase =
		'btn btn-sm btn-square min-h-8 h-8 w-8 bg-transparent hover:bg-base-200/80 border-0 shadow-none';

	function activityBtnClass(show: boolean, hasSibling: boolean) {
		const rounded = hasSibling ? 'rounded-l-xl rounded-r-none' : 'rounded-xl';
		const state = show ? 'bg-primary/15 text-primary' : 'opacity-45';
		return `${btnBase} ${rounded} ${state}`;
	}

	function trailBtnClass(show: boolean, hasSibling: boolean) {
		const rounded = hasSibling ? 'rounded-r-xl rounded-l-none' : 'rounded-xl';
		const state = show ? 'bg-[#a855f7]/15 text-[#a855f7]' : 'opacity-45';
		return `${btnBase} ${rounded} ${state}`;
	}
</script>

{#if hasActivities || hasTrails}
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
					class={activityBtnClass(showActivities, hasTrails)}
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
					class={trailBtnClass(showTrails, hasActivities)}
					aria-pressed={showTrails}
					aria-label={showTrails ? $t('map.hide_trails') : $t('map.show_trails')}
					title={showTrails ? $t('map.hide_trails') : $t('map.show_trails')}
					on:click={() => (showTrails = !showTrails)}
				>
					<HikingIcon class="w-5 h-5" />
				</button>
			{/if}
		</div>
	</div>
{/if}
