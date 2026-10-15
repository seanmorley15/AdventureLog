<script lang="ts">
	import type { Snippet } from 'svelte';
	import { untrack } from 'svelte';
	import { t } from 'svelte-i18n';
	import DateInput from '$lib/components/shared/DateInput.svelte';
	import { LODGING_TYPES_ICONS, TRANSPORTATION_TYPES_ICONS } from '$lib';
	import {
		CatalogFilters,
		catalogCounts,
		facetChecked,
		toggleFacet,
		uniqueCategoryNames,
		uniqueLodgingTypes,
		uniqueTransportTypes
	} from '$lib/collections/catalog.svelte';
	import type { Collection } from '$lib/types';
	import Magnify from '~icons/mdi/magnify';
	import FilterIcon from '~icons/mdi/filter-variant';
	import ChevronDown from '~icons/mdi/chevron-down';
	import Close from '~icons/mdi/close';
	import Eye from '~icons/mdi/eye-outline';
	import MapMarker from '~icons/mdi/map-marker';
	import Tag from '~icons/mdi/tag-outline';
	import Calendar from '~icons/mdi/calendar-range';
	import Sort from '~icons/mdi/sort';
	import Bed from '~icons/mdi/bed';
	import Airplane from '~icons/mdi/airplane';
	import Routes from '~icons/mdi/map-marker-path';

	interface Props {
		filters: CatalogFilters;
		collection: Collection;
		/** GPX, trails, and photo pins. Shared with the standalone collection map. */
		showMapToggles?: boolean;
		/** Optional numbered day pins. Catalog only; the planner map stays numbered. */
		showDayNumbers?: boolean;
		/** Notes, checklists, and sort. The list uses these; the map does not. */
		showCatalog?: boolean;
		matchedCount?: number;
		totalCount?: number;
		/** Hide the trails toggle when the collection has none. Omit to always show it. */
		trailCount?: number | null;
		imagePinCount?: number | null;
		startOpen?: boolean;
		class?: string;
	}

	let {
		filters,
		collection,
		showMapToggles = false,
		showDayNumbers = false,
		showCatalog = false,
		matchedCount = 0,
		totalCount = 0,
		trailCount = null,
		imagePinCount = null,
		startOpen = true,
		class: className = ''
	}: Props = $props();

	let open = $state(untrack(() => startOpen));
	const counts = $derived(catalogCounts(collection));
	const categories = $derived(uniqueCategoryNames(collection));
	const lodgingTypes = $derived(uniqueLodgingTypes(collection));
	const transportTypes = $derived(uniqueTransportTypes(collection));
	const pristine = $derived(filters.isPristine());
	const collectionStart = $derived(collection.start_date?.slice(0, 10) || undefined);
	const collectionEnd = $derived(collection.end_date?.slice(0, 10) || undefined);
	const showTrails = $derived(showMapToggles && trailCount !== 0);
	const showPhotos = $derived(showMapToggles && imagePinCount !== 0);
	const showDisplay = $derived(showMapToggles || showDayNumbers);

	function lodgingIcon(type: string): string {
		return LODGING_TYPES_ICONS[type as keyof typeof LODGING_TYPES_ICONS] ?? '🏨';
	}

	function transportIcon(type: string): string {
		return TRANSPORTATION_TYPES_ICONS[type as keyof typeof TRANSPORTATION_TYPES_ICONS] ?? '✈️';
	}
</script>

{#snippet check(checked: boolean, onchange: () => void, label: string, tone = 'checkbox-primary')}
	<label class="filter-option compact-check">
		<input type="checkbox" class="checkbox checkbox-xs {tone}" {checked} {onchange} />
		<span class="min-w-0 text-sm leading-none">{label}</span>
	</label>
{/snippet}

{#snippet group(icon: Snippet, title: string, body: Snippet, action?: Snippet)}
	<div class="rounded-box bg-base-100 px-2.5 py-2">
		<div class="mb-1 flex items-center gap-2">
			<h4 class="flex min-w-0 flex-1 items-center gap-1.5 text-xs font-semibold">
				{@render icon()}
				{title}
			</h4>
			{#if action}
				{@render action()}
			{/if}
		</div>
		<div class="flex flex-wrap gap-x-3 gap-y-1">
			{@render body()}
		</div>
	</div>
{/snippet}

<section class={['card bg-base-200 shadow-xl', className]}>
	<div class="card-body gap-2 p-3 sm:p-4">
		<div class="flex items-center gap-2">
			<span
				class="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"
			>
				<FilterIcon class="h-4 w-4" />
			</span>
			<h3 class="min-w-0 flex-1 text-base font-bold">{$t('adventures.filter')}</h3>
			{#if totalCount}
				<span class="badge badge-ghost whitespace-nowrap">{matchedCount}/{totalCount}</span>
			{/if}
			{#if !pristine}
				<button type="button" class="btn btn-xs btn-ghost" onclick={() => filters.reset()}>
					{$t('adventures.reset_filters')}
				</button>
			{/if}
			<button
				type="button"
				class="btn btn-xs btn-ghost btn-square"
				aria-expanded={open}
				aria-label={open ? $t('adventures.hide_filters') : $t('adventures.show_filters')}
				onclick={() => (open = !open)}
			>
				<ChevronDown class={['h-5 w-5 transition-transform', open && 'rotate-180']} />
			</button>
		</div>

		<label class="input input-sm flex w-full items-center gap-2 bg-base-100">
			<Magnify class="h-4 w-4 shrink-0 opacity-60" />
			<input
				type="text"
				class="grow"
				placeholder={$t('collections.search_items')}
				bind:value={filters.search}
			/>
			{#if filters.search}
				<button
					type="button"
					class="btn btn-ghost btn-xs btn-circle"
					aria-label={$t('adventures.clear_search')}
					onclick={() => (filters.search = '')}
				>
					<Close class="h-3.5 w-3.5" />
				</button>
			{/if}
		</label>

		{#if open}
			<div class="grid gap-2 sm:grid-cols-2">
				{@render group(visitIcon, $t('adventures.visits'), visitBody)}
				{@render group(pinIcon, $t('adventures.pins'), pinBody)}
				{#if categories.length}
					{@render group(categoryIcon, $t('adventures.categories'), categoryBody, categoryClear)}
				{/if}
				{#if showDisplay}
					{@render group(displayIcon, $t('map.display_options'), displayBody)}
				{/if}
				{#if lodgingTypes.length > 1}
					{@render group(lodgingIconHeading, $t('adventures.lodging'), lodgingBody)}
				{/if}
				{#if transportTypes.length > 1}
					{@render group(transportIconHeading, $t('adventures.transportation'), transportBody)}
				{/if}
				{@render group(dateIcon, $t('adventures.dates'), dateBody)}
				{#if showCatalog}
					{@render group(sortIcon, $t('adventures.sort'), sortBody)}
				{/if}
			</div>
		{/if}
	</div>
</section>

{#snippet visitIcon()}
	<Eye class="h-3.5 w-3.5" />
{/snippet}
{#snippet visitBody()}
	{@render check(
		filters.showVisited,
		() => (filters.showVisited = !filters.showVisited),
		$t('adventures.visited'),
		'checkbox-success'
	)}
	{@render check(
		filters.showPlanned,
		() => (filters.showPlanned = !filters.showPlanned),
		$t('adventures.planned'),
		'checkbox-info'
	)}
{/snippet}

{#snippet pinIcon()}
	<MapMarker class="h-3.5 w-3.5" />
{/snippet}
{#snippet pinBody()}
	{#if counts.locations}
		{@render check(
			filters.showLocations,
			() => (filters.showLocations = !filters.showLocations),
			`${$t('locations.locations')} (${counts.locations})`
		)}
	{/if}
	{#if counts.lodging}
		{@render check(
			filters.showLodging,
			() => (filters.showLodging = !filters.showLodging),
			`${$t('adventures.lodging')} (${counts.lodging})`,
			'checkbox-secondary'
		)}
	{/if}
	{#if counts.transportations}
		{@render check(
			filters.showTransportation,
			() => (filters.showTransportation = !filters.showTransportation),
			`${$t('adventures.transportation')} (${counts.transportations})`,
			'checkbox-accent'
		)}
	{/if}
	{#if showCatalog && counts.notes}
		{@render check(
			filters.showNotes,
			() => (filters.showNotes = !filters.showNotes),
			`${$t('adventures.notes')} (${counts.notes})`
		)}
	{/if}
	{#if showCatalog && counts.checklists}
		{@render check(
			filters.showChecklists,
			() => (filters.showChecklists = !filters.showChecklists),
			`${$t('adventures.checklists')} (${counts.checklists})`
		)}
	{/if}
{/snippet}

{#snippet categoryIcon()}
	<Tag class="h-3.5 w-3.5" />
{/snippet}
{#snippet categoryClear()}
	{#if filters.categories.size}
		<button
			type="button"
			class="btn btn-ghost btn-xs"
			onclick={() => (filters.categories = new Set())}
		>
			{$t('adventures.clear')}
		</button>
	{/if}
{/snippet}
{#snippet categoryBody()}
	{#each categories as category (category)}
		{@render check(
			facetChecked(filters.categories, category),
			() => (filters.categories = toggleFacet(filters.categories, category, categories)),
			category
		)}
	{/each}
{/snippet}

{#snippet lodgingIconHeading()}
	<Bed class="h-3.5 w-3.5" />
{/snippet}
{#snippet lodgingBody()}
	{#each lodgingTypes as type (type)}
		{@render check(
			facetChecked(filters.lodgingTypes, type),
			() => (filters.lodgingTypes = toggleFacet(filters.lodgingTypes, type, lodgingTypes)),
			`${lodgingIcon(type)} ${type}`,
			'checkbox-secondary'
		)}
	{/each}
{/snippet}

{#snippet transportIconHeading()}
	<Airplane class="h-3.5 w-3.5" />
{/snippet}
{#snippet transportBody()}
	{#each transportTypes as type (type)}
		{@render check(
			facetChecked(filters.transportTypes, type),
			() => (filters.transportTypes = toggleFacet(filters.transportTypes, type, transportTypes)),
			`${transportIcon(type)} ${type}`,
			'checkbox-accent'
		)}
	{/each}
{/snippet}

{#snippet dateIcon()}
	<Calendar class="h-3.5 w-3.5" />
{/snippet}
{#snippet dateBody()}
	<div class="flex w-full basis-full gap-1.5">
		<DateInput
			bind:value={filters.startDate}
			size="xs"
			min={collectionStart}
			max={collectionEnd}
			clearable={true}
			placeholder={$t('adventures.start_date')}
			class="min-w-0 flex-1"
		/>
		<DateInput
			bind:value={filters.endDate}
			size="xs"
			min={collectionStart}
			max={collectionEnd}
			clearable={true}
			placeholder={$t('adventures.end_date')}
			class="min-w-0 flex-1"
		/>
	</div>
{/snippet}

{#snippet sortIcon()}
	<Sort class="h-3.5 w-3.5" />
{/snippet}
{#snippet sortBody()}
	<select class="select select-xs w-full basis-full bg-base-100" bind:value={filters.sort}>
		<option value="name-asc">{$t('adventures.name')} · {$t('adventures.ascending')}</option>
		<option value="name-desc">{$t('adventures.name')} · {$t('adventures.descending')}</option>
		<option value="visited">{$t('adventures.visited')}</option>
		<option value="date-asc">{$t('adventures.start_date')}</option>
		<option value="date-desc">{$t('adventures.end_date')}</option>
	</select>
{/snippet}

{#snippet displayIcon()}
	<Routes class="h-3.5 w-3.5" />
{/snippet}
{#snippet displayBody()}
	{#if showMapToggles}
		{@render check(
			filters.showLines,
			() => (filters.showLines = !filters.showLines),
			$t('adventures.gpx_routes')
		)}
	{/if}
	{#if showTrails}
		{@render check(
			filters.showTrails,
			() => (filters.showTrails = !filters.showTrails),
			trailCount ? `${$t('adventures.trails')} (${trailCount})` : $t('adventures.trails'),
			'checkbox-secondary'
		)}
	{/if}
	{#if showPhotos}
		{@render check(
			filters.showImagePins,
			() => (filters.showImagePins = !filters.showImagePins),
			imagePinCount ? `${$t('map.photos')} (${imagePinCount})` : $t('map.photos'),
			'checkbox-error'
		)}
	{/if}
	{#if showDayNumbers}
		{@render check(
			filters.numberedPins,
			() => (filters.numberedPins = !filters.numberedPins),
			$t('collections.day_numbers')
		)}
	{/if}
{/snippet}

<style>
	.compact-check {
		width: auto;
		gap: 0.375rem;
		padding-block: 0.125rem;
	}
</style>
