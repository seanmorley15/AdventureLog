<script lang="ts">
	import type { Collection } from '$lib/types';
	import { planPins } from '$lib/dayPlan';
	import CollectionMap from './CollectionMap.svelte';
	import TripDayPlanner from './TripDayPlanner.svelte';
	import type { LinkScope } from './LinkItemsModal.svelte';

	interface Props {
		collection: Collection;
		user: any;
		canModify?: boolean;
		readMode?: boolean;
		onOpenLink?: (scope: LinkScope) => void;
	}

	let {
		collection = $bindable(),
		user,
		canModify = false,
		readMode = false,
		onOpenLink
	}: Props = $props();

	let selectedDay = $state<number | null>(null);
	let highlightedDay = $state<number | null>(null);

	const pins = $derived(planPins(collection));

	function scrollToPin(type: string, objectId: string, dayIndex: number | null) {
		const id = `plan-${type}-${objectId}-day-${dayIndex ?? 'ideas'}`;
		document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
	}
</script>

<div class="relative h-full min-h-0 lg:grid lg:grid-cols-2 lg:gap-4">
	<div
		class="h-[42%] overflow-hidden rounded-box lg:col-start-2 lg:row-start-1 lg:h-full lg:min-h-0"
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
		/>
	</div>

	<div
		class="absolute inset-x-0 bottom-0 top-[34%] z-10 overflow-y-auto overscroll-contain rounded-t-3xl bg-base-100 px-2 pb-8 shadow-2xl lg:static lg:z-auto lg:col-start-1 lg:row-start-1 lg:h-full lg:min-h-0 lg:overflow-y-auto lg:rounded-none lg:bg-transparent lg:px-0 lg:pb-2 lg:shadow-none"
	>
		<div class="mx-auto mb-3 mt-2 h-1.5 w-12 rounded-full bg-base-300 lg:hidden"></div>
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
	</div>
</div>
