<script lang="ts">
	import { t } from 'svelte-i18n';
	import type { ProfilePoint } from './activityForm.js';

	interface Props {
		/** Elevation against distance along the track, in meters. */
		profile: ProfilePoint[];
		measurementSystem?: 'metric' | 'imperial';
		class?: string;
	}

	let { profile, measurementSystem = 'metric', class: className = '' }: Props = $props();

	const HEIGHT = 144;
	const PAD = { top: 10, right: 12, bottom: 22, left: 44 };

	const imperial = $derived(measurementSystem === 'imperial');
	const distanceUnit = $derived(imperial ? 'mi' : 'km');
	const elevationUnit = $derived(imperial ? 'ft' : 'm');
	const toDistance = (meters: number) => (imperial ? meters / 1609.34 : meters / 1000);
	const toElevation = (meters: number) => (imperial ? meters * 3.28084 : meters);

	let width = $state(0);
	let hovered = $state<number | null>(null);

	const maxDistance = $derived(profile.at(-1)?.distance ?? 0);
	const elevations = $derived(profile.map((point) => toElevation(point.elevation)));
	const low = $derived(elevations.length ? Math.min(...elevations) : 0);
	const high = $derived(elevations.length ? Math.max(...elevations) : 0);
	// A flat track still needs a visible band, so the line does not sit on the axis.
	const span = $derived(Math.max(high - low, 10));
	const floor = $derived(low - span * 0.08);
	const ceiling = $derived(high + span * 0.08);

	const x = (meters: number) =>
		PAD.left + (maxDistance ? (meters / maxDistance) * (width - PAD.left - PAD.right) : 0);
	const y = (value: number) =>
		PAD.top + (1 - (value - floor) / (ceiling - floor)) * (HEIGHT - PAD.top - PAD.bottom);

	const line = $derived(
		profile
			.map(
				(point, index) =>
					`${index ? 'L' : 'M'}${x(point.distance).toFixed(1)},${y(elevations[index]).toFixed(1)}`
			)
			.join('')
	);
	const area = $derived(
		profile.length
			? `${line}L${x(maxDistance).toFixed(1)},${HEIGHT - PAD.bottom}L${x(0).toFixed(1)},${HEIGHT - PAD.bottom}Z`
			: ''
	);

	function track(event: PointerEvent) {
		const bounds = (event.currentTarget as SVGElement).getBoundingClientRect();
		const meters =
			((event.clientX - bounds.left - PAD.left) / (width - PAD.left - PAD.right)) * maxDistance;
		let nearest = 0;
		for (let i = 1; i < profile.length; i++) {
			if (Math.abs(profile[i].distance - meters) < Math.abs(profile[nearest].distance - meters))
				nearest = i;
		}
		hovered = nearest;
	}
</script>

{#if profile.length > 1}
	<div class={className} bind:clientWidth={width}>
		<div class="mb-1 flex h-5 items-center justify-between text-xs text-base-content/70">
			<span class="font-semibold">{$t('activities.elevation_profile')}</span>
			{#if hovered != null}
				<span class="tabular-nums">
					{toDistance(profile[hovered].distance).toFixed(2)}
					{distanceUnit} · {Math.round(elevations[hovered])}
					{elevationUnit}
				</span>
			{/if}
		</div>
		{#if width > 0}
			<svg
				{width}
				height={HEIGHT}
				role="img"
				aria-label={$t('activities.elevation_profile')}
				class="touch-none text-primary"
				onpointermove={track}
				onpointerleave={() => (hovered = null)}
			>
				{#each [low, (low + high) / 2, high] as tick (tick)}
					<line
						x1={PAD.left}
						x2={width - PAD.right}
						y1={y(tick)}
						y2={y(tick)}
						class="stroke-base-content/10"
					/>
					<text
						x={PAD.left - 6}
						y={y(tick) + 3}
						text-anchor="end"
						class="fill-base-content/60 text-[10px]"
					>
						{Math.round(tick)}
					</text>
				{/each}
				<path d={area} fill="currentColor" fill-opacity="0.18" />
				<path d={line} fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" />
				<text x={PAD.left} y={HEIGHT - 6} class="fill-base-content/60 text-[10px]">0</text>
				<text
					x={width - PAD.right}
					y={HEIGHT - 6}
					text-anchor="end"
					class="fill-base-content/60 text-[10px]"
				>
					{toDistance(maxDistance).toFixed(1)}
					{distanceUnit}
				</text>
				{#if hovered != null}
					<line
						x1={x(profile[hovered].distance)}
						x2={x(profile[hovered].distance)}
						y1={PAD.top}
						y2={HEIGHT - PAD.bottom}
						class="stroke-base-content/40"
					/>
					<circle
						cx={x(profile[hovered].distance)}
						cy={y(elevations[hovered])}
						r="4"
						fill="currentColor"
						class="stroke-base-100"
						stroke-width="2"
					/>
				{/if}
			</svg>
		{/if}
	</div>
{/if}
