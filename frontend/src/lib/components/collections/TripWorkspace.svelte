<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { Collection } from '#lib/types.js';
	import { planPins } from '#lib/collections/plan.js';
	import { CatalogFilters } from '#lib/collections/catalog.svelte.js';
	import CollectionMap from './CollectionMap.svelte';
	import TripDayPlanner from './TripDayPlanner.svelte';
	import type { LinkScope } from './LinkItemsModal.svelte';

	interface Props {
		collection: Collection;
		user: any;
		canModify?: boolean;
		readMode?: boolean;
		/** Folders show the catalog beside a clustered, auto-framed map. */
		folder?: boolean;
		onOpenLink?: (scope: LinkScope) => void;
		children?: Snippet<[CatalogFilters]>;
	}

	let {
		collection = $bindable(),
		user,
		canModify = false,
		readMode = false,
		folder = false,
		onOpenLink,
		children
	}: Props = $props();

	const catalogFilters = new CatalogFilters();

	// On touch phones the map sits inside the scrolling page, so a one-finger swipe should scroll
	// the page rather than pan the map. MapLibre reads this once, when the map is created.
	const touchPhone =
		typeof window !== 'undefined' &&
		window.matchMedia('(pointer: coarse) and (max-width: 1023px)').matches;

	let selectedDay = $state<number | null>(null);
	let highlightedDay = $state<number | null>(null);

	const pins = $derived(planPins(collection));

	function scrollToPin(type: string, objectId: string, dayIndex: number | null) {
		const ids = [
			`plan-${type}-${objectId}-day-${dayIndex ?? 'ideas'}`,
			`catalog-${type}-${objectId}`
		];
		for (const id of ids) {
			const el = document.getElementById(id);
			if (el) {
				el.scrollIntoView({ behavior: 'smooth', block: 'center' });
				return;
			}
		}
	}
</script>

<!-- Phones: the map sits on top and the plan list flows below it, so both scroll with the page.
     Desktop: map and plan list side by side, each filling the height under the tab bar. -->
<div class="relative flex flex-col gap-3 lg:grid lg:h-full lg:min-h-0 lg:grid-cols-2 lg:gap-4">
	<div
		class="h-[45dvh] min-h-64 shrink-0 overflow-hidden rounded-box lg:col-start-2 lg:row-start-1 lg:h-full lg:min-h-0"
	>
		<CollectionMap
			bind:collection
			{user}
			canModify={canModify && !readMode}
			embedded
			mapClass="h-full w-full"
			planPins={pins}
			{selectedDay}
			{highlightedDay}
			onPinSelect={scrollToPin}
			filters={children ? catalogFilters : undefined}
			numberedPins={!children}
			pinStyleToggle={Boolean(children) && !folder}
			clusterEnabled={folder}
			clusterOptions={{ radius: 300, maxZoom: 8, minPoints: 2 }}
			autoFit={folder}
			dayPicker={!children}
			cooperativeGestures={touchPhone}
		/>
	</div>

	<div
		class="planner-pane pb-8 lg:col-start-1 lg:row-start-1 lg:h-full lg:min-h-0 lg:overflow-x-hidden lg:overflow-y-auto lg:overscroll-contain lg:pb-2"
	>
		{#if children}
			{@render children(catalogFilters)}
		{:else}
			<TripDayPlanner
				bind:collection
				{user}
				{canModify}
				{readMode}
				{selectedDay}
				onSelectDay={(day) => (selectedDay = selectedDay === day ? null : day)}
				onHighlightDay={(day) => (highlightedDay = day)}
				{onOpenLink}
			/>
		{/if}
	</div>
</div>

<style>
	.planner-pane {
		scrollbar-width: none;
	}
	.planner-pane::-webkit-scrollbar {
		display: none;
	}
</style>
