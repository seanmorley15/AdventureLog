<script lang="ts">
	import { t } from 'svelte-i18n';
	import type { Attachment } from 'svelte/attachments';
	import EarthIcon from '~icons/mdi/earth';
	import { attachPopoverFlip } from '$lib/utils/flipDropdown';

	const browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

	interface Props {
		selectedTimezone?: string;
		label?: string | null;
		size?: 'xs' | 'sm' | 'md';
		class?: string;
	}

	let {
		selectedTimezone = $bindable(),
		label = null,
		size = 'md',
		class: className
	}: Props = $props();

	if (!selectedTimezone) {
		selectedTimezone = browserTimezone;
	}

	const uid = $props.id();
	const instanceId = `tz-selector-${uid}`;
	const popoverId = `${instanceId}-popover`;
	const anchorName = `--${instanceId.replace(/[^a-zA-Z0-9_-]/g, '')}`;

	let labelText = $derived(label ?? ($t('adventures.timezone') as string));
	const sizeClass = $derived(size === 'xs' ? 'input-xs' : size === 'sm' ? 'input-sm' : '');
	const iconClass = $derived(
		size === 'md' ? 'size-4 shrink-0 opacity-60' : 'size-3.5 shrink-0 opacity-60'
	);

	let searchQuery = $state('');
	let searchInput: HTMLInputElement | undefined;
	let popoverElement: HTMLDivElement | undefined = $state();
	const timezones = Intl.supportedValuesOf('timeZone');

	let filteredTimezones = $derived(
		searchQuery
			? timezones.filter((tz) => tz.toLowerCase().includes(searchQuery.toLowerCase()))
			: timezones
	);

	function selectTimezone(tz: string) {
		selectedTimezone = tz;
		searchQuery = '';
		// Close after this click finishes so the same click cannot reopen the trigger.
		setTimeout(() => popoverElement?.hidePopover(), 0);
	}

	function handleTriggerKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			event.preventDefault();
			popoverElement?.hidePopover();
		}
	}

	const captureSearch: Attachment<HTMLInputElement> = (element) => {
		searchInput = element;
		return () => {
			if (searchInput === element) searchInput = undefined;
		};
	};

	const managePopover: Attachment<HTMLDivElement> = (element) => {
		popoverElement = element;
		const triggerId = `timezone-display-${instanceId}`;
		const detachFlip = attachPopoverFlip(element, () => document.getElementById(triggerId), 320);
		const onToggle = (event: Event) => {
			if ((event as ToggleEvent).newState !== 'open') return;
			searchQuery = '';
			requestAnimationFrame(() => {
				searchInput?.focus();
				element.querySelector('[aria-selected="true"]')?.scrollIntoView({ block: 'nearest' });
			});
		};
		element.addEventListener('toggle', onToggle);
		return () => {
			detachFlip();
			element.removeEventListener('toggle', onToggle);
			if (popoverElement === element) popoverElement = undefined;
		};
	};
</script>

<div class={['tz-field flex w-full min-w-0 flex-col', className]} id={instanceId}>
	<label class="field-label" for={`timezone-display-${instanceId}`}>{labelText}</label>

	<button
		id={`timezone-display-${instanceId}`}
		type="button"
		popovertarget={popoverId}
		aria-haspopup="listbox"
		class={['input tz-trigger justify-between font-normal', sizeClass]}
		style:anchor-name={anchorName}
		onkeydown={handleTriggerKeydown}
	>
		<EarthIcon class={iconClass} />
		<span class="truncate min-w-0 flex-1 text-left">{selectedTimezone}</span>
		<svg
			xmlns="http://www.w3.org/2000/svg"
			class="w-4 h-4 shrink-0 opacity-60"
			fill="none"
			viewBox="0 0 24 24"
			stroke="currentColor"
			aria-hidden="true"
		>
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
		</svg>
	</button>
</div>

<div
	{@attach managePopover}
	popover
	id={popoverId}
	class="dropdown tz-popover bg-base-100 rounded-box shadow-lg"
	style:position-anchor={anchorName}
>
	<div class="tz-search">
		<input
			type="text"
			placeholder="Search timezone"
			class="input input-sm w-full"
			{@attach captureSearch}
			bind:value={searchQuery}
		/>
	</div>

	<div class="tz-list" role="listbox" aria-labelledby={`timezone-display-${instanceId}`}>
		{#if filteredTimezones.length > 0}
			{#each filteredTimezones as tz (tz)}
				<button
					type="button"
					class={[
						'tz-option btn btn-sm btn-block justify-start font-normal',
						tz === selectedTimezone ? 'btn-primary' : 'btn-ghost'
					]}
					onclick={() => selectTimezone(tz)}
					role="option"
					aria-selected={tz === selectedTimezone}
				>
					{tz}
				</button>
			{/each}
		{:else}
			<div class="p-3 text-sm text-center opacity-60">No timezones found</div>
		{/if}
	</div>
</div>

<style>
	.tz-trigger {
		width: 100%;
		max-width: none;
	}

	.tz-popover {
		width: anchor-size(width);
		min-width: 16rem;
		padding: 0.5rem;
		overflow: hidden;
	}

	.tz-search {
		padding-bottom: 0.5rem;
	}

	.tz-search :global(.input) {
		width: 100%;
		max-width: none;
	}

	.tz-list {
		display: flex;
		flex-direction: column;
		gap: 0.15rem;
		max-height: 16rem;
		overflow-y: auto;
		scrollbar-width: thin;
	}

	.tz-option {
		width: 100%;
		max-width: none;
		justify-content: flex-start;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
</style>
