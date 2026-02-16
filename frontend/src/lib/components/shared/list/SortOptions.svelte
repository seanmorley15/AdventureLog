<script lang="ts">
	/**
	 * SortOptions - Sort direction and order by options (collapsible)
	 */
	import { createEventDispatcher } from 'svelte';
	import { t } from 'svelte-i18n';
	import Sort from '~icons/mdi/sort';

	export let orderBy: string = 'updated_at';
	export let orderDirection: string = 'asc';
	export let orderByOptions: { value: string; label: string }[] = [
		{ value: 'updated_at', label: 'Updated' },
		{ value: 'name', label: 'Name' },
		{ value: 'last_visit', label: 'Last Visit' },
		{ value: 'created_at', label: 'Created' },
		{ value: 'rating', label: 'Rating' }
	];
	export let collapsed: boolean = false;

	const dispatch = createEventDispatcher<{ change: { orderBy: string; orderDirection: string } }>();

	function handleDirectionChange(direction: string) {
		orderDirection = direction;
		dispatch('change', { orderBy, orderDirection });
	}

	function handleOrderByChange(value: string) {
		orderBy = value;
		dispatch('change', { orderBy, orderDirection });
	}

	$: activeOrderLabel = orderByOptions.find((o) => o.value === orderBy)?.label || '';
</script>

<div class="collapse collapse-arrow bg-base-200/50 rounded-box">
	<input type="checkbox" checked={!collapsed} />
	<div class="collapse-title font-medium flex items-center gap-2 py-2 min-h-0">
		<Sort class="w-5 h-5" />
		{$t('adventures.sort')}
		<span class="badge badge-ghost badge-sm">{activeOrderLabel} {orderDirection === 'asc' ? '↑' : '↓'}</span>
	</div>
	<div class="collapse-content !pb-2">
		<div class="space-y-2">
			<div>
				<div class="join w-full">
					<button
						class="join-item btn btn-sm flex-1 {orderDirection === 'asc' ? 'btn-active' : ''}"
						on:click={() => handleDirectionChange('asc')}
					>
						{$t('adventures.ascending')}
					</button>
					<button
						class="join-item btn btn-sm flex-1 {orderDirection === 'desc' ? 'btn-active' : ''}"
						on:click={() => handleDirectionChange('desc')}
					>
						{$t('adventures.descending')}
					</button>
				</div>
			</div>

			<div class="space-y-0">
				{#each orderByOptions as option}
					<label class="flex items-center gap-2 cursor-pointer py-0.5">
						<input
							type="radio"
							name="order_by_radio"
							class="radio radio-primary radio-sm"
							checked={orderBy === option.value}
							on:change={() => handleOrderByChange(option.value)}
						/>
						<span>{option.label}</span>
					</label>
				{/each}
			</div>
		</div>
	</div>
</div>
