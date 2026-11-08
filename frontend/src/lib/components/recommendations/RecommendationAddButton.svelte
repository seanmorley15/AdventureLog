<script lang="ts">
	import { t } from 'svelte-i18n';
	import Plus from '~icons/mdi/plus';
	import ChevronDown from '~icons/mdi/chevron-down';
	import Bed from '~icons/mdi/bed';

	export type DayOption = { date: string; label: string };

	interface Props {
		busy?: boolean;
		/** The primary click adds lodging, not a location. */
		lodging?: boolean;
		/** Offer "Add as lodging" in the menu. */
		canAddLodging?: boolean;
		days?: DayOption[];
		onAdd: () => void;
		onAddToDay: (date: string) => void;
		onAddDetails: () => void;
		onAddLodging: () => void;
	}

	let {
		busy = false,
		lodging = false,
		canAddLodging = false,
		days = [],
		onAdd,
		onAddToDay,
		onAddDetails,
		onAddLodging
	}: Props = $props();

	let open = $state(false);
	let root = $state<HTMLElement | null>(null);

	function pick(action: () => void) {
		open = false;
		action();
	}
</script>

<svelte:window
	onclick={(event) => {
		if (open && root && !root.contains(event.target as Node)) open = false;
	}}
	onkeydown={(event) => {
		if (event.key === 'Escape') open = false;
	}}
/>

<div class="flex gap-px" bind:this={root}>
	<button
		type="button"
		class="btn btn-primary btn-sm gap-1 rounded-r-none"
		disabled={busy}
		onclick={onAdd}
	>
		{#if busy}
			<span class="loading loading-spinner loading-xs"></span>
		{:else if lodging}
			<Bed class="h-4 w-4" />
		{:else}
			<Plus class="h-4 w-4" />
		{/if}
		{$t('recomendations.add')}
	</button>
	<div class="relative">
		<button
			type="button"
			class="btn btn-primary btn-sm rounded-l-none px-2"
			aria-label={$t('recomendations.more_options')}
			aria-haspopup="menu"
			aria-expanded={open}
			onclick={() => (open = !open)}
		>
			<ChevronDown class="h-4 w-4" />
		</button>
		{#if open}
			<ul
				class="menu absolute right-0 top-full z-30 mt-1 w-56 rounded-box bg-base-100 p-2 shadow-xl"
			>
				{#each days as day (day.date)}
					<li>
						<button type="button" disabled={busy} onclick={() => pick(() => onAddToDay(day.date))}>
							{$t('recomendations.add_to_day', { values: { day: day.label } })}
						</button>
					</li>
				{/each}
				<li>
					<button type="button" disabled={busy} onclick={() => pick(onAddDetails)}>
						{$t('map.add_with_details')}
					</button>
				</li>
				{#if canAddLodging}
					<li>
						<button type="button" disabled={busy} onclick={() => pick(onAddLodging)}>
							{$t('map.add_as_lodging')}
						</button>
					</li>
				{/if}
			</ul>
		{/if}
	</div>
</div>
