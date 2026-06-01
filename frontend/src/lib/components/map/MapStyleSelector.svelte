<script lang="ts">
	import { basemapOptions, getBasemapLabel } from '$lib';

	import MapIcon from '~icons/mdi/map';

	export let basemapType: string = 'default';

	const categoryOrder = [
		'Standard',
		'3D Terrain',
		'Satellite',
		'Topographic',
		'Clean',
		'Specialized'
	];

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
</script>

<div class="dropdown dropdown-left">
	<div
		tabindex="0"
		role="button"
		aria-haspopup="menu"
		aria-expanded="false"
		class="btn btn-sm btn-ghost gap-2 min-h-0 h-8 px-3"
	>
		<MapIcon class="w-4 h-4" />
		<span class="text-xs font-medium">{getBasemapLabel(basemapType)}</span>
		<svg class="w-3 h-3 fill-none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
		</svg>
	</div>
	{#if basemapOptions?.length}
		<div
			tabindex="-1"
			class="dropdown-content z-20 shadow-lg bg-base-200 rounded-box w-54 max-h-80 overflow-y-auto overflow-x-hidden p-3"
			role="menu"
		>
			{#each categoryOrder as category}
				{#if groupedOptions[category]?.length}
					<div class="mb-2 last:mb-0">
						<p class="px-2 pb-1 text-xs uppercase tracking-wide text-base-content/60">{category}</p>
						<ul class="space-y-1">
							{#each groupedOptions[category] as option}
								<li>
									<button
										class="flex items-center gap-3 px-3 py-2 text-sm rounded-md transition-colors {basemapType ===
										option.value
											? 'bg-primary/10 font-medium'
											: 'hover:bg-base-300/60'}"
										on:pointerdown={(e) => {
											e.preventDefault();
											e.stopPropagation();
											basemapType = option.value;
										}}
										on:click={() => (basemapType = option.value)}
										role="menuitem"
									>
										<span class="text-lg">{option.icon}</span>
										<span class="truncate">{option.label}</span>
										{#if basemapType === option.value}
											<svg
												class="w-4 h-4 ml-auto text-primary"
												fill="currentColor"
												viewBox="0 0 20 20"
											>
												<path
													fill-rule="evenodd"
													d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
													clip-rule="evenodd"
												/>
											</svg>
										{/if}
									</button>
								</li>
							{/each}
						</ul>
					</div>
				{/if}
			{/each}
		</div>
	{/if}
</div>
