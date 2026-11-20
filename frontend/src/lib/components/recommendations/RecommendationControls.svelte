<script lang="ts">
	import { t } from 'svelte-i18n';
	import { searchPlaces } from '#lib/map/places.js';
	import type { PlaceSearchResult } from '#lib/types.js';
	import FilterChip from '#lib/components/shared/FilterChip.svelte';
	import {
		RECOMMENDATION_CATEGORIES,
		type RecommendationCategory
	} from '#lib/recommendations/categories.js';
	import Compass from '~icons/mdi/compass';
	import MapMarker from '~icons/mdi/map-marker';
	import Magnify from '~icons/mdi/magnify';
	import Crosshairs from '~icons/mdi/crosshairs-gps';

	export type Anchor =
		| { kind: 'map' }
		| { kind: 'point'; id: string; label: string; lat: number; lng: number };
	export type AnchorOption = { id: string; label: string; group: string; lat: number; lng: number };
	export type SortMode = 'best' | 'nearest' | 'rating';

	interface Props {
		category: RecommendationCategory;
		radius: number;
		radiusOptions: { value: number; label: string }[];
		sort: SortMode;
		hideAdded: boolean;
		anchor: Anchor;
		anchorOptions: AnchorOption[];
		onAnchor: (anchor: Anchor) => void;
	}

	let {
		category = $bindable(),
		radius = $bindable(),
		radiusOptions,
		sort = $bindable(),
		hideAdded = $bindable(),
		anchor,
		anchorOptions,
		onAnchor
	}: Props = $props();

	let query = $state('');
	let results = $state<PlaceSearchResult[]>([]);
	let searching = $state(false);
	let menu = $state<HTMLDetailsElement | null>(null);
	let timer: ReturnType<typeof setTimeout> | null = null;
	let requestId = 0;

	const groups = $derived.by(() => {
		const out = new Map<string, AnchorOption[]>();
		for (const option of anchorOptions) {
			out.set(option.group, [...(out.get(option.group) ?? []), option]);
		}
		return [...out.entries()];
	});

	const anchorLabel = $derived(
		anchor.kind === 'map' ? $t('recomendations.this_map_area') : anchor.label
	);

	function choose(next: Anchor) {
		if (menu) menu.open = false;
		query = '';
		results = [];
		onAnchor(next);
	}

	function onQuery() {
		if (timer) clearTimeout(timer);
		const text = query.trim();
		if (text.length < 3) {
			results = [];
			searching = false;
			return;
		}
		searching = true;
		const id = ++requestId;
		timer = setTimeout(async () => {
			try {
				const found = await searchPlaces(text);
				if (id === requestId) results = found.results.slice(0, 6);
			} catch {
				if (id === requestId) results = [];
			} finally {
				if (id === requestId) searching = false;
			}
		}, 300);
	}
</script>

<div class="space-y-3">
	<div class="flex items-center gap-3">
		<Compass class="h-5 w-5 shrink-0 text-primary" />
		<div class="min-w-0 flex-1">
			<h3 class="text-lg font-bold">{$t('recomendations.recommendations')}</h3>
			<p class="text-sm opacity-70">{$t('recomendations.subtitle')}</p>
		</div>
	</div>

	<div class="space-y-1.5">
		<p class="text-[11px] font-semibold uppercase tracking-wide text-base-content/50">
			{$t('recomendations.search_near')}
		</p>
		<details class="dropdown w-full" bind:this={menu}>
			<summary class="btn btn-sm w-full justify-start gap-2 bg-base-100 font-normal">
				{#if anchor.kind === 'map'}
					<Crosshairs class="h-4 w-4 text-primary" />
				{:else}
					<MapMarker class="h-4 w-4 text-primary" />
				{/if}
				<span class="truncate">{anchorLabel}</span>
			</summary>
			<div
				class="dropdown-content z-30 mt-1 max-h-80 w-full overflow-y-auto rounded-box bg-base-100 p-2 shadow-xl"
			>
				<label class="input input-sm mb-2 flex w-full items-center gap-2">
					<Magnify class="h-4 w-4 opacity-60" />
					<input
						type="text"
						class="grow"
						placeholder={$t('recomendations.search_place_placeholder')}
						bind:value={query}
						oninput={onQuery}
					/>
					{#if searching}<span class="loading loading-spinner loading-xs"></span>{/if}
				</label>
				<ul class="menu menu-sm w-full p-0">
					{#each results as place (place.id)}
						<li>
							<button
								type="button"
								onclick={() =>
									choose({
										kind: 'point',
										id: `search-${place.id}`,
										label: place.name,
										lat: place.lat,
										lng: place.lng
									})}
							>
								<span class="min-w-0">
									<span class="block truncate font-medium">{place.name}</span>
									<span class="block truncate text-xs opacity-60">{place.location}</span>
								</span>
							</button>
						</li>
					{/each}
					{#if !results.length}
						<li>
							<button type="button" onclick={() => choose({ kind: 'map' })}>
								<Crosshairs class="h-4 w-4" />
								{$t('recomendations.this_map_area')}
							</button>
						</li>
						{#each groups as [group, options] (group)}
							<li class="menu-title">{group}</li>
							{#each options as option (option.id)}
								<li>
									<button
										type="button"
										onclick={() =>
											choose({
												kind: 'point',
												id: option.id,
												label: option.label,
												lat: option.lat,
												lng: option.lng
											})}
									>
										<span class="truncate">{option.label}</span>
									</button>
								</li>
							{/each}
						{/each}
					{/if}
				</ul>
			</div>
		</details>
	</div>

	<div class="flex flex-wrap gap-1.5">
		{#each RECOMMENDATION_CATEGORIES as option (option.key)}
			<FilterChip active={category === option.key} onclick={() => (category = option.key)}>
				{option.emoji}
				{$t(option.labelKey)}
			</FilterChip>
		{/each}
	</div>

	<div class="space-y-1.5">
		<p class="text-[11px] font-semibold uppercase tracking-wide text-base-content/50">
			{$t('map.recommendation_radius')}
		</p>
		<div class="flex flex-wrap gap-1.5">
			{#each radiusOptions as option (option.value)}
				<FilterChip active={radius === option.value} onclick={() => (radius = option.value)}>
					{option.label}
				</FilterChip>
			{/each}
		</div>
	</div>

	<div class="flex flex-wrap items-center gap-3">
		<select
			class="select select-sm w-auto"
			bind:value={sort}
			aria-label={$t('recomendations.sort')}
		>
			<option value="best">{$t('recomendations.sort_best')}</option>
			<option value="nearest">{$t('recomendations.sort_nearest')}</option>
			<option value="rating">{$t('recomendations.sort_rating')}</option>
		</select>
		<label class="flex cursor-pointer items-center gap-2 text-sm">
			<input type="checkbox" class="toggle toggle-sm toggle-primary" bind:checked={hideAdded} />
			{$t('recomendations.hide_added')}
		</label>
	</div>
</div>
