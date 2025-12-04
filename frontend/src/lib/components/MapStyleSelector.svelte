<script lang="ts">
	import { basemapOptions, getBasemapLabel } from '$lib';

	import MapIcon from '~icons/mdi/map';

	export let basemapType: string = 'default';
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
	<ul class="dropdown-content z-20 menu p-2 shadow-lg bg-base-200 rounded-box w-48">
		{#each basemapOptions as option}
			<li>
				<button
					class="flex items-center gap-3 px-3 py-2 text-sm rounded-md transition-colors {basemapType ===
					option.value
						? 'bg-primary/10  font-medium'
						: ''}"
					on:pointerdown={(e) => {
						e.preventDefault();
						e.stopPropagation();
						basemapType = option.value;
					}}
					on:click={() => (basemapType = option.value)}
					role="menuitem"
				>
					<span class="text-lg">{option.icon}</span>
					<span>{option.label}</span>
					{#if basemapType === option.value}
						<svg class="w-4 h-4 ml-auto text-primary" fill="currentColor" viewBox="0 0 20 20">
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
