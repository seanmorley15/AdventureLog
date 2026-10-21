<script lang="ts">
	import { t } from 'svelte-i18n';
	import type { Collection, Pin } from '$lib/types';
	import { objectsOfType, placementType, type PlanObjectType } from '$lib/collections/plan';
	import Close from '~icons/mdi/close';
	import Magnify from '~icons/mdi/magnify';
	import MapMarker from '~icons/mdi/map-marker';
	import Bed from '~icons/mdi/bed';
	import Airplane from '~icons/mdi/airplane';
	import NoteText from '~icons/mdi/note-text';
	import ListChecks from '~icons/mdi/format-list-checks';
	import Plus from '~icons/mdi/plus';
	import Check from '~icons/mdi/check';

	export type LinkScope =
		| { kind: 'collection' }
		| { kind: 'ideas' }
		| { kind: 'day'; index: number }
		| { kind: 'global' };

	interface Props {
		collection: Collection;
		scope: LinkScope;
		onAdd: (type: PlanObjectType, id: string) => Promise<void>;
		onClose: () => void;
	}

	let { collection, scope, onAdd, onClose }: Props = $props();

	type Filter = 'all' | PlanObjectType;
	type Row = {
		type: PlanObjectType;
		id: string;
		name: string;
		detail: string | null;
		icon?: string | null;
	};

	const FILTERS: { id: Filter; label: string }[] = [
		{ id: 'all', label: 'adventures.all' },
		{ id: 'location', label: 'locations.locations' },
		{ id: 'lodging', label: 'adventures.lodging' },
		{ id: 'transportation', label: 'adventures.transportation' },
		{ id: 'note', label: 'adventures.notes' },
		{ id: 'checklist', label: 'adventures.checklists' }
	];

	let query = $state('');
	let filter = $state<Filter>('all');
	let pins = $state<Pin[]>([]);
	let loading = $state(true);
	let loadingMore = $state(false);
	let total = $state(0);
	let hasMore = $state(false);
	let searching = $state(false);
	let anchored = $state(false);
	let busyId = $state<string | null>(null);
	let added = $state<Set<string>>(new Set());
	let searchTimer: ReturnType<typeof setTimeout> | null = null;

	const allowed = $derived(
		scope.kind === 'global'
			? (['note', 'checklist'] as PlanObjectType[])
			: scope.kind === 'collection'
				? (['location'] as PlanObjectType[])
				: (['location', 'lodging', 'transportation', 'note', 'checklist'] as PlanObjectType[])
	);

	const linkedIds = $derived(
		new Set((collection.locations ?? []).map((location) => String(location.id)))
	);
	const plannedIds = $derived(
		new Set(
			(collection.itinerary ?? [])
				.filter((item) => item.day_index != null)
				.map((item) => String(item.object_id))
		)
	);

	const placementLabel = $derived.by(() => {
		const labels = new Map<string, string[]>();
		for (const item of collection.itinerary ?? []) {
			if (placementType(item) == null) continue;
			const label = item.is_global
				? $t('itinerary.trip_wide')
				: item.day_index
					? $t('itinerary.on_day', { values: { n: item.day_index } })
					: $t('itinerary.in_ideas');
			const key = String(item.object_id);
			labels.set(key, [...(labels.get(key) ?? []), label]);
		}
		return labels;
	});

	const title = $derived(
		scope.kind === 'day'
			? $t('itinerary.add_to_day', { values: { n: scope.index } })
			: scope.kind === 'ideas'
				? $t('itinerary.add_to_ideas')
				: scope.kind === 'global'
					? $t('itinerary.trip_wide')
					: $t('itinerary.add_to_collection')
	);

	const needle = $derived(query.trim().toLowerCase());

	const locationRows = $derived.by(() => {
		if (!allowed.includes('location') || (filter !== 'all' && filter !== 'location')) return [];
		const list: Row[] = [];
		for (const pin of pins) {
			if (needle && !pin.name.toLowerCase().includes(needle)) continue;
			list.push({
				type: 'location',
				id: pin.id,
				name: pin.name,
				detail: pin.category?.display_name ?? null,
				icon: pin.category?.icon ?? null
			});
		}
		return list;
	});

	const otherRows = $derived.by(() => {
		if (filter === 'location') return [];
		const list: Row[] = [];
		for (const type of allowed) {
			if (type === 'location' || (filter !== 'all' && filter !== type)) continue;
			for (const obj of objectsOfType(collection, type)) {
				const name = 'name' in obj ? obj.name : '';
				if (needle && !name.toLowerCase().includes(needle)) continue;
				list.push({ type, id: String(obj.id), name, detail: null });
			}
		}
		return list;
	});

	const visible = $derived([...otherRows, ...locationRows]);

	const PAGE_SIZE = 30;

	async function loadPlaces(term = '', offset = 0) {
		const params = new URLSearchParams({
			collection: collection.id,
			limit: String(PAGE_SIZE),
			offset: String(offset)
		});
		if (term) params.set('q', term);
		const response = await fetch(`/api/locations/suggest/?${params}`);
		if (!response.ok) return { results: [] as Pin[], anchored: false, count: 0 };
		return (await response.json()) as { results: Pin[]; anchored: boolean; count: number };
	}

	function applyPage(data: Awaited<ReturnType<typeof loadPlaces>>, append = false) {
		pins = append ? [...pins, ...(data.results ?? [])] : (data.results ?? []);
		anchored = Boolean(data.anchored);
		total = data.count ?? pins.length;
		hasMore = pins.length < total;
	}

	function open(node: HTMLDialogElement) {
		node.showModal();
		let cancelled = false;
		if (allowed.includes('location')) {
			void loadPlaces()
				.then((data) => {
					if (!cancelled) applyPage(data);
				})
				.finally(() => {
					if (!cancelled) loading = false;
				});
		} else {
			loading = false;
		}
		return () => {
			cancelled = true;
			if (searchTimer) clearTimeout(searchTimer);
			node.close();
		};
	}

	function onQuery(value: string) {
		query = value;
		if (searchTimer) clearTimeout(searchTimer);
		const term = value.trim().length < 2 ? '' : value.trim();
		searching = true;
		searchTimer = setTimeout(async () => {
			const data = await loadPlaces(term);
			if ((query.trim().length < 2 ? '' : query.trim()) !== term) return;
			applyPage(data);
			searching = false;
		}, 250);
	}

	async function loadMore() {
		if (loadingMore || !hasMore) return;
		loadingMore = true;
		try {
			const term = query.trim().length < 2 ? '' : query.trim();
			applyPage(await loadPlaces(term, pins.length), true);
		} finally {
			loadingMore = false;
		}
	}

	async function add(row: Row) {
		const key = `${row.type}:${row.id}`;
		if (busyId || added.has(key)) return;
		busyId = key;
		try {
			await onAdd(row.type, row.id);
			added = new Set(added).add(key);
		} finally {
			busyId = null;
		}
	}
</script>

<dialog
	class="modal modal-bottom backdrop-blur-xs md:modal-middle"
	{@attach open}
	onclose={onClose}
>
	<div
		class="link-items-modal modal-box flex flex-col overflow-hidden rounded-none border border-base-300 bg-base-100 p-0 shadow-2xl md:rounded-2xl"
		role="dialog"
		aria-labelledby="link-items-title"
	>
		<div class="shrink-0 border-b border-base-300 bg-base-100 px-4 py-3 md:px-6 md:py-4">
			<div class="flex items-center justify-between gap-3">
				<div class="flex min-w-0 items-center gap-3">
					<div class="shrink-0 rounded-xl bg-primary/10 p-2 text-primary">
						<MapMarker class="h-8 w-8" />
					</div>
					<div class="min-w-0">
						<h1 id="link-items-title" class="truncate text-2xl font-bold text-primary md:text-3xl">
							{title}
						</h1>
						<p class="truncate text-sm text-base-content/80">{$t('itinerary.add_existing_hint')}</p>
					</div>
				</div>
				<button
					type="button"
					class="btn btn-ghost btn-square shrink-0"
					aria-label={$t('about.close')}
					onclick={onClose}
				>
					<Close class="h-5 w-5" />
				</button>
			</div>
		</div>

		<div
			class="flex shrink-0 flex-col gap-3 border-b border-base-300 bg-base-200/40 px-4 py-3 md:px-6"
		>
			<label class="input input-md w-full bg-base-100">
				<Magnify class="h-4 w-4 opacity-60" />
				<input
					type="search"
					placeholder={$t('itinerary.search_items')}
					value={query}
					oninput={(event) => onQuery(event.currentTarget.value)}
				/>
			</label>

			<div class="flex flex-wrap items-center justify-between gap-2">
				{#if allowed.length > 1}
					<div class="flex flex-wrap gap-1.5">
						{#each FILTERS.filter((item) => item.id === 'all' || allowed.includes(item.id as PlanObjectType)) as item (item.id)}
							<button
								type="button"
								class="btn btn-sm rounded-full {filter === item.id
									? 'btn-primary'
									: 'btn-ghost border-base-300'}"
								onclick={() => (filter = item.id)}
							>
								{$t(item.label)}
							</button>
						{/each}
					</div>
				{:else}
					<span class="text-sm font-semibold">{$t('itinerary.your_places')}</span>
				{/if}
				{#if allowed.includes('location') && !loading}
					<span class="text-xs text-base-content/60">
						{$t('itinerary.showing_count', { values: { shown: pins.length, total } })}
						· {anchored && needle.length < 2
							? $t('itinerary.sorted_nearest')
							: $t('itinerary.sorted_name')}
					</span>
				{/if}
			</div>
		</div>

		<div class="min-h-0 flex-1 overflow-y-auto px-4 py-4 md:px-6">
			{#if loading || searching}
				<div class="flex justify-center py-16">
					<span class="loading loading-spinner loading-lg text-primary"></span>
				</div>
			{:else if visible.length === 0}
				<p class="py-16 text-center text-sm text-base-content/60">
					{$t('itinerary.no_matching_items')}
				</p>
			{:else}
				<div class="grid gap-2 md:grid-cols-2">
					{#each visible as row (`${row.type}:${row.id}`)}
						{@const key = `${row.type}:${row.id}`}
						{@const where = placementLabel.get(row.id)}
						{@const inCollection = row.type === 'location' && linkedIds.has(row.id)}
						{@const done =
							added.has(key) ||
							(scope.kind === 'ideas' && plannedIds.has(row.id)) ||
							(inCollection && scope.kind === 'collection')}
						<div
							class="flex items-center gap-3 rounded-xl border border-base-300 bg-base-100 px-3 py-2.5 transition-colors {done
								? 'opacity-70'
								: 'hover:border-primary/40 hover:bg-base-200/40'}"
						>
							<div
								class="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-primary/10 text-lg text-primary"
							>
								{#if row.type === 'lodging'}
									<Bed class="h-5 w-5" />
								{:else if row.type === 'transportation'}
									<Airplane class="h-5 w-5" />
								{:else if row.type === 'note'}
									<NoteText class="h-5 w-5" />
								{:else if row.type === 'checklist'}
									<ListChecks class="h-5 w-5" />
								{:else if row.icon}
									<span aria-hidden="true">{row.icon}</span>
								{:else}
									<MapMarker class="h-5 w-5" />
								{/if}
							</div>
							<div class="min-w-0 flex-1">
								<p class="truncate font-semibold">{row.name}</p>
								<div class="flex flex-wrap items-center gap-1.5">
									{#if row.detail}
										<span class="truncate text-xs text-base-content/60">{row.detail}</span>
									{/if}
									{#if where}
										{#each where as label, index (index)}
											<span class="badge badge-outline badge-sm">{label}</span>
										{/each}
									{/if}
								</div>
							</div>
							{#if done}
								<span class="badge badge-success badge-soft gap-1 whitespace-nowrap">
									<Check class="h-3.5 w-3.5" />
									{added.has(key) ? $t('itinerary.added') : $t('itinerary.already_in_collection')}
								</span>
							{:else}
								<button
									type="button"
									class="btn btn-sm btn-primary gap-1"
									disabled={busyId !== null}
									onclick={() => add(row)}
								>
									{#if busyId === key}
										<span class="loading loading-spinner loading-xs"></span>
									{:else}
										<Plus class="h-4 w-4" />
									{/if}
									{$t('adventures.add')}
								</button>
							{/if}
						</div>
					{/each}
				</div>
				{#if hasMore && filter !== 'note' && filter !== 'checklist'}
					<div class="flex justify-center pt-4">
						<button type="button" class="btn btn-outline btn-sm" onclick={loadMore}>
							{#if loadingMore}<span class="loading loading-spinner loading-xs"></span>{/if}
							{$t('itinerary.load_more')}
						</button>
					</div>
				{/if}
			{/if}
		</div>

		<div
			class="flex shrink-0 items-center justify-between border-t border-base-300 px-4 py-3 md:px-6"
		>
			<span class="text-sm text-base-content/60">
				{#if added.size}{$t('itinerary.added_n', { values: { n: added.size } })}{/if}
			</span>
			<button type="button" class="btn btn-primary" onclick={onClose}
				>{$t('adventures.done')}</button
			>
		</div>
	</div>
	<form method="dialog" class="modal-backdrop">
		<button type="button" onclick={onClose}>{$t('about.close')}</button>
	</form>
</dialog>

<style>
	.link-items-modal {
		width: 100%;
		max-width: 100%;
		height: 100dvh;
		max-height: 100dvh;
	}

	@media (min-width: 768px) {
		.link-items-modal {
			width: min(96vw, 72rem);
			max-width: 72rem;
			height: min(90dvh, 56rem);
			max-height: 90dvh;
		}
	}
</style>
