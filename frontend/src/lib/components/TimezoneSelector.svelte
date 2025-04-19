<script lang="ts">
	import { t } from 'svelte-i18n';
	import { onMount } from 'svelte';

	export let selectedTimezone: string = Intl.DateTimeFormat().resolvedOptions().timeZone;

	let dropdownOpen = false;
	let searchQuery = '';
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

	// Close dropdown if clicked outside
	onMount(() => {
		const handleClickOutside = (e: MouseEvent) => {
			const dropdown = document.getElementById('tz-selector');
			if (dropdown && !dropdown.contains(e.target as Node)) dropdownOpen = false;
		};
		document.addEventListener('click', handleClickOutside);
		return () => document.removeEventListener('click', handleClickOutside);
	});
</script>

<div class="form-control w-full max-w-xs relative" id="tz-selector">
	<label class="label">
		<span class="label-text">Timezone</span>
	</label>

	<!-- Trigger -->
	<div
		tabindex="0"
		role="button"
		class="input input-bordered flex justify-between items-center cursor-pointer"
		on:click={() => (dropdownOpen = !dropdownOpen)}
	>
		<span class="truncate">{selectedTimezone}</span>
		<svg
			xmlns="http://www.w3.org/2000/svg"
			class="w-4 h-4"
			fill="none"
			viewBox="0 0 24 24"
			stroke="currentColor"
		>
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
		</svg>
	</div>

	<!-- Dropdown -->
	{#if dropdownOpen}
		<div
			class="absolute mt-1 z-10 bg-base-100 shadow-lg rounded-box w-full max-h-60 overflow-y-auto"
		>
			<!-- Search -->
			<div class="sticky top-0 bg-base-100 p-2 border-b">
				<input
					type="text"
					placeholder="Search timezone"
					class="input input-sm input-bordered w-full"
					bind:value={searchQuery}
					autofocus
				/>
			</div>

			<!-- Timezone list -->
			{#if filteredTimezones.length > 0}
				<ul class="menu p-2 space-y-1">
					{#each filteredTimezones as tz}
						<li>
							<a
								class={`truncate ${tz === selectedTimezone ? 'active font-bold' : ''}`}
								on:click|preventDefault={() => selectTimezone(tz)}
							>
								{tz}
							</a>
						</li>
					{/each}
				</ul>
			{:else}
				<div class="p-2 text-sm text-center opacity-60">No timezones found</div>
			{/if}
		</div>
	{/if}
</div>
