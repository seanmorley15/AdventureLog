<script lang="ts">
	import type { PriceTier } from '$lib/types';
	import { t } from 'svelte-i18n';

	export let priceTier: PriceTier = null;
	export let showTooltip: boolean = true;
	export let badgeClass: string = 'badge-success badge-sm';

	// Convert tier number to money icons
	$: tierIcons = priceTier ? '💰'.repeat(priceTier.tier) : null;

	// Tier labels
	const tierLabels: Record<number, string> = {
		1: 'budget',
		2: 'moderate',
		3: 'expensive',
		4: 'premium'
	};

	$: tierLabel = priceTier ? $t(`adventures.price_tier_${tierLabels[priceTier.tier]}`) || tierLabels[priceTier.tier] : null;
</script>

{#if priceTier && tierIcons}
	{#if showTooltip}
		<div class="tooltip tooltip-bottom" data-tip="{tierLabel} ({priceTier.country_name})">
			<span class="badge {badgeClass} whitespace-nowrap cursor-help">
				{tierIcons}
			</span>
		</div>
	{:else}
		<span class="badge {badgeClass} whitespace-nowrap">
			{tierIcons}
		</span>
	{/if}
{/if}
