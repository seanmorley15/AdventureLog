<script lang="ts">
	import type { Snippet } from 'svelte';
	import CheckIcon from '~icons/mdi/check';

	interface Props {
		active?: boolean;
		tone?: 'primary' | 'secondary' | 'accent' | 'success' | 'info' | 'error';
		disabled?: boolean;
		onclick?: () => void;
		children: Snippet;
	}

	let { active = false, tone = 'primary', disabled = false, onclick, children }: Props = $props();
</script>

<button
	type="button"
	class={['filter-chip', active && `filter-chip-on filter-chip-${tone}`]}
	aria-pressed={active}
	{disabled}
	{onclick}
>
	{#if active}<CheckIcon class="h-3 w-3" />{/if}
	{@render children()}
</button>

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
	.filter-chip:disabled {
		opacity: 0.5;
		cursor: not-allowed;
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
