<script lang="ts">
	import { basemapOptions, getBasemapLabel } from '$lib';
	import { t } from 'svelte-i18n';
	import MapIcon from '~icons/mdi/map';
	import CheckIcon from '~icons/mdi/check';

	export let basemapType: string = 'default';
	/** DaisyUI dropdown placement classes */
	export let dropdownClass = 'dropdown dropdown-left';

	const categoryOrder = [
		'Standard',
		'3D Terrain',
		'Satellite',
		'Topographic',
		'Clean',
		'Specialized'
	] as const;

	const groupedOptions = basemapOptions.reduce<Record<string, typeof basemapOptions>>(
		(acc, option) => {
			if (!acc[option.category]) {
				acc[option.category] = [];
			}
			acc[option.category].push(option);
			return acc;
		},
		{}
	);

	let dropdownOpen = false;
	let dropdownEl: HTMLDivElement;

	function selectBasemap(value: string) {
		basemapType = value;
		dropdownOpen = false;
	}

	function toggleDropdown() {
		dropdownOpen = !dropdownOpen;
	}

	function closeDropdown(event: MouseEvent) {
		if (!dropdownOpen) return;
		if (dropdownEl?.contains(event.target as Node)) return;
		dropdownOpen = false;
	}
</script>

<svelte:window on:click={closeDropdown} />

<div bind:this={dropdownEl} class="{dropdownClass} {dropdownOpen ? 'dropdown-open' : ''}">
	<button
		type="button"
		class="btn btn-sm btn-ghost gap-1.5 min-h-0 h-8 px-2 sm:px-3"
		aria-haspopup="menu"
		aria-expanded={dropdownOpen}
		on:click={toggleDropdown}
	>
		<MapIcon class="w-4 h-4 shrink-0" />
		<span class="text-xs font-medium hidden sm:inline truncate max-w-[5.5rem] md:max-w-none">
			{getBasemapLabel(basemapType)}
		</span>
		<svg class="w-3 h-3 shrink-0 fill-none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
		</svg>
	</button>

	{#if basemapOptions?.length}
		<div
			class="dropdown-content z-[100] shadow-xl bg-base-100 rounded-xl border border-base-300 w-56 sm:w-60 p-0"
			role="menu"
			tabindex="-1"
		>
			<div class="px-3 py-2 border-b border-base-300/80">
				<p class="text-[11px] font-semibold uppercase tracking-wide text-base-content/50">
					{$t('map.map_style')}
				</p>
			</div>

			<div class="max-h-64 overflow-y-auto overscroll-contain py-1">
				{#each categoryOrder as category}
					{#if groupedOptions[category]?.length}
						<div class="px-2 pt-2 pb-0.5 first:pt-1">
							<p
								class="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-base-content/45 sticky top-0 bg-base-100/95 backdrop-blur-sm z-[1]"
							>
								{category}
							</p>
							<ul class="flex flex-col gap-0.5">
								{#each groupedOptions[category] as option (option.value)}
									<li>
										<button
											type="button"
											class="flex items-center gap-2 w-full px-2 py-1.5 text-left text-sm rounded-md transition-colors {basemapType ===
											option.value
												? 'bg-primary/15 text-primary font-medium'
												: 'hover:bg-base-200/80'}"
											on:click={() => selectBasemap(option.value)}
											role="menuitemradio"
											aria-checked={basemapType === option.value}
										>
											<span class="text-sm shrink-0 w-5 text-center" aria-hidden="true"
												>{option.icon}</span
											>
											<span class="truncate flex-1 min-w-0">{option.label}</span>
											{#if basemapType === option.value}
												<CheckIcon class="w-3.5 h-3.5 shrink-0" />
											{/if}
										</button>
									</li>
								{/each}
							</ul>
						</div>
					{/if}
				{/each}
			</div>
		</div>
	{/if}
</div>
