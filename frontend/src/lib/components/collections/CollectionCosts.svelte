<script lang="ts">
	import { t } from 'svelte-i18n';
	import type { Collection } from '#lib/types.js';
	import { DEFAULT_CURRENCY } from '#lib/money.js';
	import { buildCostEntries, summarizeCostEntries } from '#lib/collections/costs.js';

	interface Props {
		collection: Collection;
		currency?: string;
	}

	let { collection, currency = DEFAULT_CURRENCY }: Props = $props();

	const locale = Intl.DateTimeFormat().resolvedOptions().locale;
	const labels = $derived({
		lodging: $t('adventures.lodging'),
		transportation: $t('adventures.transportation'),
		location: $t('locations.locations')
	});
	const summary = $derived(
		summarizeCostEntries(buildCostEntries(collection, currency), locale, labels)
	);
</script>

<div class="card bg-base-200 shadow-xl">
	<div class="card-body space-y-4">
		<h3 class="card-title text-lg">{$t('collections.trip_costs')}</h3>
		{#if summary.length === 0}
			<p class="text-sm opacity-70">{$t('collections.no_priced_items')}</p>
		{:else}
			{#each summary as group (group.currency)}
				<div class="space-y-2 rounded-lg bg-base-300 p-3">
					<div class="flex items-center justify-between">
						<span class="badge badge-outline badge-sm">{group.currency}</span>
						<span class="text-lg font-bold">{group.formattedTotal}</span>
					</div>
					{#each group.categories as category (`${group.currency}-${category.category}`)}
						<div class="flex items-center justify-between text-sm">
							<span class="opacity-70">{category.label} ({category.count})</span>
							<span class="font-semibold">{category.formattedTotal}</span>
						</div>
					{/each}
				</div>
			{/each}
		{/if}
	</div>
</div>
