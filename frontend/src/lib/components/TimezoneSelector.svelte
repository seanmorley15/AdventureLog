<script lang="ts">
	import { t } from 'svelte-i18n';
	import { onMount } from 'svelte';

	export let selectedTimezone: string = Intl.DateTimeFormat().resolvedOptions().timeZone;
	// Generate a unique ID for this component instance
	const uniqueId = Date.now().toString(36) + Math.random().toString(36).substring(2);
	const instanceId = `tz-selector-${uniqueId}`;

	let dropdownOpen = false;
	let searchQuery = '';
	let searchInput: HTMLInputElement | null = null;
	let rootRef: HTMLElement | null = null;
	const timezones = Intl.supportedValuesOf('timeZone');

	// Filter timezones based on search query
	$: filteredTimezones = searchQuery
		? timezones.filter((tz) => tz.toLowerCase().includes(searchQuery.toLowerCase()))
		: timezones;

	function selectTimezone(tz: string) {
		selectedTimezone = tz;
		dropdownOpen = false;
		searchQuery = '';
	}

	// Focus search input when dropdown opens - with proper null check
	$: if (dropdownOpen && searchInput) {
		// Use setTimeout to delay focus until after the element is rendered
		setTimeout(() => {
			if (searchInput) searchInput.focus();
		}, 0);
	}

	function handleKeydown(event: KeyboardEvent, tz?: string) {
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();
			if (tz) selectTimezone(tz);
			else dropdownOpen = !dropdownOpen;
		} else if (event.key === 'Escape') {
			event.preventDefault();
			dropdownOpen = false;
		}
	}

	// Close dropdown if clicked/touched outside. Use composedPath and pointer events
	onMount(() => {
		const handlePointerDownOutside = (e: Event) => {
			const ev: any = e as any;
			const path: EventTarget[] = ev.composedPath ? ev.composedPath() : ev.path || [];
			if (!rootRef) return;
			if (Array.isArray(path)) {
				if (!path.includes(rootRef)) dropdownOpen = false;
			} else {
				if (!(e.target instanceof Node) || !(rootRef as HTMLElement).contains(e.target as Node))
					dropdownOpen = false;
			}
		};

		document.addEventListener('pointerdown', handlePointerDownOutside, true);
		document.addEventListener('touchstart', handlePointerDownOutside, true);
		return () => {
			document.removeEventListener('pointerdown', handlePointerDownOutside, true);
			document.removeEventListener('touchstart', handlePointerDownOutside, true);
		};
	});
</script>

<div class="form-control w-full max-w-xs relative" bind:this={rootRef} id={instanceId}>
	<label class="label" for={`timezone-display-${instanceId}`}>
		<span class="label-text">{$t('adventures.timezone')}</span>
	</label>

	<!-- Trigger -->
	<div
		id={`timezone-display-${instanceId}`}
		tabindex="0"
		role="button"
		aria-haspopup="listbox"
		aria-expanded={dropdownOpen}
		class="input input-bordered flex justify-between items-center cursor-pointer"
		on:pointerdown={(e) => {
			e.preventDefault();
			e.stopPropagation();
			dropdownOpen = !dropdownOpen;
		}}
		on:click={() => (dropdownOpen = !dropdownOpen)}
		on:keydown={handleKeydown}
	>
		<span class="truncate">{selectedTimezone}</span>
		<svg
			xmlns="http://www.w3.org/2000/svg"
			class="w-4 h-4"
			fill="none"
			viewBox="0 0 24 24"
			stroke="currentColor"
			aria-hidden="true"
		>
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
		</svg>
	</div>

	<!-- Dropdown -->
	{#if dropdownOpen}
		<div
			class="absolute mt-1 z-10 bg-base-100 shadow-lg rounded-box w-full max-h-60 overflow-y-auto"
			role="listbox"
			aria-labelledby={`timezone-display-${instanceId}`}
		>
			<!-- Search -->
			<div class="sticky top-0 bg-base-100 p-2 border-b">
				<input
					type="text"
					placeholder="Search timezone"
					class="input input-sm input-bordered w-full"
					bind:value={searchQuery}
					bind:this={searchInput}
				/>
			</div>

			<!-- Timezone list -->
			{#if filteredTimezones.length > 0}
				<ul class="menu p-2 space-y-1">
					{#each filteredTimezones as tz}
						<li>
							<button
								type="button"
								class={`w-full text-left truncate ${tz === selectedTimezone ? 'active font-bold' : ''}`}
								on:pointerdown={(e) => {
									e.preventDefault();
									e.stopPropagation();
									selectTimezone(tz);
								}}
								on:click={() => selectTimezone(tz)}
								on:keydown={(e) => handleKeydown(e, tz)}
								role="option"
								aria-selected={tz === selectedTimezone}
							>
								{tz}
							</button>
						</li>
					{/each}
				</ul>
			{:else}
				<div class="p-2 text-sm text-center opacity-60">No timezones found</div>
			{/if}
		</div>
	{/if}
</div>
