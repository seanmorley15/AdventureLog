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
	import CheckIcon from '~icons/mdi/check';
	import ChevronDown from '~icons/mdi/chevron-down';
	import Close from '~icons/mdi/close';
	import Tag from '~icons/mdi/tag-outline';
	import Calendar from '~icons/mdi/calendar-range';
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
		startOpen = false,
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
	const advancedCount = $derived(
		(filters.categories.size ? 1 : 0) +
			(filters.lodgingTypes.size ? 1 : 0) +
			(filters.transportTypes.size ? 1 : 0) +
			(filters.startDate ? 1 : 0) +
			(filters.endDate ? 1 : 0) +
			(!filters.showLines || !filters.showTrails || !filters.showImagePins ? 1 : 0) +
			(filters.numberedPins ? 1 : 0)
	);

	function lodgingIcon(type: string): string {
		return LODGING_TYPES_ICONS[type as keyof typeof LODGING_TYPES_ICONS] ?? '🏨';
	}

	function transportIcon(type: string): string {
		return TRANSPORTATION_TYPES_ICONS[type as keyof typeof TRANSPORTATION_TYPES_ICONS] ?? '✈️';
	}
</script>

{#snippet chip(active: boolean, onclick: () => void, label: string, tone = 'primary')}
	<button
		type="button"
		class={['filter-chip', active && `filter-chip-on filter-chip-${tone}`]}
		aria-pressed={active}
		{onclick}
	>
		{#if active}<CheckIcon class="h-3 w-3" />{/if}
		{label}
	</button>
{/snippet}

{#snippet section(icon: Snippet, title: string, body: Snippet, action?: Snippet)}
	<div class="space-y-1.5">
		<div class="flex items-center gap-1.5 text-xs font-semibold text-base-content/60">
			{@render icon()}
			<span class="flex-1">{title}</span>
			{#if action}{@render action()}{/if}
		</div>
		<div class="flex flex-wrap gap-1.5">{@render body()}</div>
	</div>
{/snippet}

<section class={['rounded-2xl border border-base-300/70 bg-base-100 p-3 shadow-sm', className]}>
	<div class="flex flex-wrap items-center gap-2">
		<label class="input input-sm flex min-w-40 flex-1 items-center gap-2 bg-base-200/60">
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
		{#if showCatalog}
			<select
				class="select select-sm w-auto bg-base-100"
				aria-label={$t('adventures.sort')}
				bind:value={filters.sort}
			>
				<option value="name-asc">{$t('adventures.name')} · {$t('adventures.ascending')}</option>
				<option value="name-desc">{$t('adventures.name')} · {$t('adventures.descending')}</option>
				<option value="visited">{$t('adventures.visited')}</option>
				<option value="date-asc">{$t('adventures.start_date')}</option>
				<option value="date-desc">{$t('adventures.end_date')}</option>
			</select>
		{/if}
		<button
			type="button"
			class={['btn btn-sm gap-1.5', open || advancedCount ? 'btn-primary btn-soft' : 'btn-ghost']}
			aria-expanded={open}
			aria-label={open ? $t('adventures.hide_filters') : $t('adventures.show_filters')}
			onclick={() => (open = !open)}
		>
			<FilterIcon class="h-4 w-4" />
			<span class="hidden sm:inline">{$t('adventures.filter')}</span>
			{#if advancedCount}<span class="badge badge-primary badge-xs">{advancedCount}</span>{/if}
		</button>
	</div>

	<div class="mt-2.5 flex flex-wrap items-center gap-1.5">
		{#if counts.locations}
			{@render chip(
				filters.showLocations,
				() => (filters.showLocations = !filters.showLocations),
				`${$t('locations.locations')} ${counts.locations}`
			)}
		{/if}
		{#if counts.lodging}
			{@render chip(
				filters.showLodging,
				() => (filters.showLodging = !filters.showLodging),
				`${$t('adventures.lodging')} ${counts.lodging}`,
				'secondary'
			)}
		{/if}
		{#if counts.transportations}
			{@render chip(
				filters.showTransportation,
				() => (filters.showTransportation = !filters.showTransportation),
				`${$t('adventures.transportation')} ${counts.transportations}`,
				'accent'
			)}
		{/if}
		{#if showCatalog && counts.notes}
			{@render chip(
				filters.showNotes,
				() => (filters.showNotes = !filters.showNotes),
				`${$t('adventures.notes')} ${counts.notes}`
			)}
		{/if}
		{#if showCatalog && counts.checklists}
			{@render chip(
				filters.showChecklists,
				() => (filters.showChecklists = !filters.showChecklists),
				`${$t('adventures.checklists')} ${counts.checklists}`
			)}
		{/if}
		<span class="mx-1 hidden h-4 w-px bg-base-300 sm:block"></span>
		{@render chip(
			filters.showVisited,
			() => (filters.showVisited = !filters.showVisited),
			$t('adventures.visited'),
			'success'
		)}
		{@render chip(
			filters.showPlanned,
			() => (filters.showPlanned = !filters.showPlanned),
			$t('adventures.planned'),
			'info'
		)}
		<span class="ml-auto flex items-center gap-2 text-xs text-base-content/60">
			{#if totalCount}<span class="whitespace-nowrap">{matchedCount}/{totalCount}</span>{/if}
			{#if !pristine}
				<button type="button" class="btn btn-xs btn-ghost" onclick={() => filters.reset()}>
					{$t('adventures.reset_filters')}
				</button>
			{/if}
		</span>
	</div>

	{#if open}
		<div class="mt-3 space-y-3 border-t border-base-300/70 pt-3">
			{#if categories.length}
				{@render section(categoryIcon, $t('adventures.categories'), categoryBody, categoryClear)}
			{/if}
			{#if lodgingTypes.length > 1}
				{@render section(lodgingIconHeading, $t('adventures.lodging'), lodgingBody)}
			{/if}
			{#if transportTypes.length > 1}
				{@render section(transportIconHeading, $t('adventures.transportation'), transportBody)}
			{/if}
			{@render section(dateIcon, $t('adventures.dates'), dateBody)}
			{#if showDisplay}
				{@render section(displayIcon, $t('map.display_options'), displayBody)}
			{/if}
		</div>
	{/if}
</section>

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
		{@render chip(
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
		{@render chip(
			facetChecked(filters.lodgingTypes, type),
			() => (filters.lodgingTypes = toggleFacet(filters.lodgingTypes, type, lodgingTypes)),
			`${lodgingIcon(type)} ${type}`,
			'secondary'
		)}
	{/each}
{/snippet}

{#snippet transportIconHeading()}
	<Airplane class="h-3.5 w-3.5" />
{/snippet}
{#snippet transportBody()}
	{#each transportTypes as type (type)}
		{@render chip(
			facetChecked(filters.transportTypes, type),
			() => (filters.transportTypes = toggleFacet(filters.transportTypes, type, transportTypes)),
			`${transportIcon(type)} ${type}`,
			'accent'
		)}
	{/each}
{/snippet}

{#snippet dateIcon()}
	<Calendar class="h-3.5 w-3.5" />
{/snippet}
{#snippet dateBody()}
	<div class="flex w-full gap-1.5">
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

{#snippet displayIcon()}
	<Routes class="h-3.5 w-3.5" />
{/snippet}
{#snippet displayBody()}
	{#if showMapToggles}
		{@render chip(
			filters.showLines,
			() => (filters.showLines = !filters.showLines),
			$t('adventures.gpx_routes')
		)}
	{/if}
	{#if showTrails}
		{@render chip(
			filters.showTrails,
			() => (filters.showTrails = !filters.showTrails),
			trailCount ? `${$t('adventures.trails')} (${trailCount})` : $t('adventures.trails'),
			'secondary'
		)}
	{/if}
	{#if showPhotos}
		{@render chip(
			filters.showImagePins,
			() => (filters.showImagePins = !filters.showImagePins),
			imagePinCount ? `${$t('map.photos')} (${imagePinCount})` : $t('map.photos'),
			'error'
		)}
	{/if}
	{#if showDayNumbers}
		{@render chip(
			filters.numberedPins,
			() => (filters.numberedPins = !filters.numberedPins),
			$t('collections.day_numbers')
		)}
	{/if}
{/snippet}

<style>
	.filter-chip {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		height: 1.75rem;
		padding-inline: 0.75rem;
		border-radius: 9999px;
		border: 1px solid var(--color-base-300);
		font-size: 0.8125rem;
		font-weight: 500;
		color: color-mix(in oklab, var(--color-base-content) 60%, transparent);
		white-space: nowrap;
		cursor: pointer;
		transition:
			background-color 0.15s,
			color 0.15s,
			border-color 0.15s;
	}
	.filter-chip:hover {
		background: var(--color-base-200);
	}
	.filter-chip-on {
		color: var(--chip-color);
		border-color: color-mix(in oklab, var(--chip-color) 40%, transparent);
		background: color-mix(in oklab, var(--chip-color) 12%, transparent);
	}
	.filter-chip-primary {
		--chip-color: var(--color-primary);
	}
	.filter-chip-secondary {
		--chip-color: var(--color-secondary);
	}
	.filter-chip-accent {
		--chip-color: var(--color-accent);
	}
	.filter-chip-success {
		--chip-color: var(--color-success);
	}
	.filter-chip-info {
		--chip-color: var(--color-info);
	}
	.filter-chip-error {
		--chip-color: var(--color-error);
	}
</style>
