<script lang="ts">
	import { t } from 'svelte-i18n';
	import type { Collection } from '$lib/types';
	import { objectsOfType, type PlanObjectType } from '$lib/dayPlan';
	import Close from '~icons/mdi/close';
	import Magnify from '~icons/mdi/magnify';

	interface Props {
		collection: Collection;
		title: string;
		/** Where each object currently sits, keyed by object id. */
		placementLabels: Map<string, string>;
		types?: PlanObjectType[];
		onPick: (type: PlanObjectType, objectId: string) => Promise<void>;
		onClose: () => void;
	}

	let { collection, title, placementLabels, types, onPick, onClose }: Props = $props();

	let query = $state('');
	let busyId = $state<string | null>(null);

	const TYPES: { type: PlanObjectType; label: string }[] = [
		{ type: 'location', label: 'locations.locations' },
		{ type: 'lodging', label: 'adventures.lodging' },
		{ type: 'transportation', label: 'adventures.transportations' },
		{ type: 'note', label: 'adventures.notes' },
		{ type: 'checklist', label: 'adventures.checklists' }
	];

	const groups = $derived.by(() => {
		const needle = query.trim().toLowerCase();
		return TYPES.filter(({ type }) => !types || types.includes(type))
			.map(({ type, label }) => ({
				type,
				label,
				objects: objectsOfType(collection, type).filter(
					(obj) => !needle || ('name' in obj && obj.name?.toLowerCase().includes(needle))
				)
			}))
			.filter((group) => group.objects.length > 0);
	});

	async function pick(type: PlanObjectType, objectId: string) {
		busyId = objectId;
		try {
			await onPick(type, objectId);
		} finally {
			busyId = null;
		}
	}
</script>

<dialog {@attach (node) => node.showModal()} class="modal" onclose={onClose}>
	<div class="modal-box flex max-h-[80vh] max-w-lg flex-col">
		<div class="mb-3 flex items-center justify-between gap-3">
			<h3 class="text-lg font-bold">{title}</h3>
			<button
				type="button"
				class="btn btn-sm btn-ghost btn-square"
				aria-label={$t('about.close')}
				onclick={onClose}
			>
				<Close class="h-4 w-4" />
			</button>
		</div>

		<label class="input mb-3 w-full">
			<Magnify class="h-4 w-4 opacity-60" />
			<input type="search" bind:value={query} placeholder={$t('itinerary.search_items')} />
		</label>

		<div class="-mx-2 min-h-0 flex-1 overflow-y-auto px-2">
			{#if groups.length === 0}
				<p class="py-6 text-center text-sm opacity-70">{$t('itinerary.no_matching_items')}</p>
			{/if}
			{#each groups as group (group.type)}
				<h4 class="mb-1 mt-3 text-xs font-semibold uppercase tracking-wide opacity-60">
					{$t(group.label)}
				</h4>
				<ul class="space-y-1">
					{#each group.objects as obj (obj.id)}
						{@const placed = placementLabels.get(String(obj.id))}
						<li>
							<button
								type="button"
								class="flex w-full items-center justify-between gap-3 rounded-lg border border-base-300 bg-base-100 px-3 py-2 text-left hover:border-primary disabled:opacity-60"
								disabled={busyId !== null}
								onclick={() => pick(group.type, String(obj.id))}
							>
								<span class="min-w-0 truncate font-medium">{'name' in obj ? obj.name : ''}</span>
								<span class="flex shrink-0 items-center gap-2 text-xs opacity-70">
									{#if busyId === String(obj.id)}
										<span class="loading loading-spinner loading-xs"></span>
									{:else if placed}
										{placed}
									{/if}
								</span>
							</button>
						</li>
					{/each}
				</ul>
			{/each}
		</div>
	</div>
	<form method="dialog" class="modal-backdrop">
		<button aria-label={$t('about.close')}>close</button>
	</form>
</dialog>
