<script lang="ts">
	import type { Snippet } from 'svelte';
	import { Marker, Popup } from 'svelte-maplibre';

	type Tone = 'visited' | 'planned' | 'lodging' | 'transportation';

	interface Props {
		lngLat: [number, number];
		/** Emoji shown in the pin, e.g. the category or mode icon. */
		icon?: string;
		/** Colors match the collection map: visited green, planned blue, lodging purple, transport amber. */
		tone?: Tone;
		/** A small caption under the pin, e.g. From / To. */
		label?: string;
		/** Popup content, shown on click. */
		children?: Snippet;
	}

	let { lngLat, icon = '📍', tone = 'planned', label = '', children }: Props = $props();

	const TONES: Record<Tone, string> = {
		visited: 'bg-gradient-to-br from-emerald-400 to-emerald-600',
		planned: 'bg-gradient-to-br from-blue-400 to-blue-600',
		lodging: 'bg-gradient-to-br from-purple-400 to-purple-600',
		transportation: 'bg-gradient-to-br from-amber-400 to-amber-600'
	};
</script>

<!-- The same round pin the collection map uses, instead of MapLibre's default teardrop. -->
<Marker {lngLat} class="map-pin">
	<div class="flex flex-col items-center gap-1">
		<div
			class="grid h-9 w-9 cursor-pointer place-items-center rounded-full border-2 border-white text-base shadow-lg transition-transform duration-200 hover:scale-110 {TONES[
				tone
			]}"
		>
			{icon}
		</div>
		{#if label}
			<span
				class="rounded-full bg-base-100 px-2 py-0.5 text-[10px] font-semibold leading-none text-base-content shadow ring-1 ring-base-300"
			>
				{label}
			</span>
		{/if}
	</div>
	{#if children}
		<Popup openOn="click" offset={[0, -22]}>
			{@render children()}
		</Popup>
	{/if}
</Marker>
