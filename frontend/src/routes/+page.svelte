<script lang="ts">
	import { goto, preloadData } from '$app/navigation';
	import { t } from 'svelte-i18n';
	import { onMount } from 'svelte';
	import type { Background } from '#lib/types.js';

	import ArrowRight from '~icons/mdi/arrow-right';
	import MapMarker from '~icons/mdi/map-marker';
	import Star from '~icons/mdi/star';
	import CalendarOutline from '~icons/mdi/calendar-outline';
	import CheckCircle from '~icons/mdi/check-circle';

	let { data } = $props();

	let background: Background = $derived(data.props?.background ?? { url: '' });
	let ready = $state(false);
	// Narrow (portrait) screens get their own map layout so the route stays in view
	let narrow = $state(false);

	// Pointer-driven parallax for the floating cards (no-op under reduced motion)
	let px = $state(0);
	let py = $state(0);
	let reduceMotion = false;

	onMount(() => {
		reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
		narrow = window.matchMedia('(max-width: 1023px)').matches;
		requestAnimationFrame(() => (ready = true));

		// Warm up the login and signup loads so the transition starts instantly
		const idle = window.requestIdleCallback ?? ((cb: () => void) => setTimeout(cb, 600));
		idle(() => {
			preloadData('/login').catch(() => {});
			preloadData('/signup').catch(() => {});
		});
	});

	function onPointerMove(e: PointerEvent) {
		if (reduceMotion) return;
		px = e.clientX / window.innerWidth - 0.5;
		py = e.clientY / window.innerHeight - 0.5;
	}

	// Topographic contour lines, generated once. Each ring is a wobbling closed path.
	function contour(level: number, cx: number, cy: number): string {
		const points: string[] = [];
		const steps = 72;
		for (let i = 0; i <= steps; i++) {
			const a = (i / steps) * Math.PI * 2;
			const wobble =
				1 +
				0.16 * Math.sin(a * 3 + level * 0.55) +
				0.1 * Math.sin(a * 5 - level * 0.8) +
				0.05 * Math.sin(a * 9 + level);
			const rx = (60 + level * 58) * wobble;
			const ry = (38 + level * 38) * wobble;
			points.push(
				`${i === 0 ? 'M' : 'L'}${(cx + Math.cos(a) * rx).toFixed(1)} ${(cy + Math.sin(a) * ry).toFixed(1)}`
			);
		}
		return points.join(' ') + 'Z';
	}
	const contoursWide = Array.from({ length: 14 }, (_, i) => contour(i + 1, 640, 360));
	const contoursTall = Array.from({ length: 14 }, (_, i) => contour(i + 1, 360, 640));

	// Route and pins for the hero overlay: landscape (1280 x 720) and portrait (720 x 1280)
	const wide = {
		viewBox: '0 0 1280 720',
		route: 'M640 660 C 720 600, 780 640, 860 540 S 1010 420, 1090 330 S 1180 190, 1230 110',
		pins: [
			{ x: 640, y: 660, d: 0 },
			{ x: 860, y: 540, d: 1 },
			{ x: 1090, y: 330, d: 2 },
			{ x: 1230, y: 110, d: 3 }
		]
	};
	// Portrait keeps the whole route in the band above the headline
	const tall = {
		viewBox: '0 0 720 1280',
		route: 'M70 330 C 160 290, 230 330, 330 250 S 500 200, 560 150 S 620 125, 650 110',
		pins: [
			{ x: 70, y: 330, d: 0 },
			{ x: 330, y: 250, d: 1 },
			{ x: 560, y: 150, d: 2 },
			{ x: 650, y: 110, d: 3 }
		]
	};
	let map = $derived(narrow ? tall : wide);
	let contours = $derived(narrow ? contoursTall : contoursWide);

	const days = [
		{ d: 'Mon', name: 'Arrive and settle in', done: true },
		{ d: 'Tue', name: 'Sunrise on the ridge', done: true },
		{ d: 'Wed', name: 'Old town and market', done: false },
		{ d: 'Thu', name: 'Day trip by rail', done: false }
	];
</script>

<svelte:window onpointermove={onPointerMove} />

<!-- ============ HERO ============ -->
<section
	class="hero relative isolate overflow-hidden bg-neutral text-white"
	class:ready
	style="--px:{px};--py:{py}"
>
	{#if background.url}
		<img
			src={background.url}
			alt={background.location ?? ''}
			class="fixed inset-0 -z-30 h-full w-full object-cover"
		/>
	{/if}
	<div class="absolute inset-0 -z-20 hero-shade"></div>

	<!-- Map layer: contours, graticule, route, pins -->
	<svg
		class="absolute inset-0 -z-10 h-full w-full"
		viewBox={map.viewBox}
		preserveAspectRatio="xMidYMid slice"
		fill="none"
		aria-hidden="true"
	>
		<g class="contours" stroke="white" stroke-width="1">
			{#each contours as d, i}
				<path {d} style="--i:{i}" />
			{/each}
		</g>
		<path d={map.route} class="route" stroke="var(--color-accent)" stroke-width="2.5" />
		{#each map.pins as pin}
			<g class="pin" style="--d:{pin.d}" transform="translate({pin.x} {pin.y})">
				<circle r="16" class="pin-ring" fill="var(--color-accent)" />
				<circle r="6" fill="var(--color-accent)" stroke="white" stroke-width="2" />
			</g>
		{/each}
	</svg>

	<!-- Graticule ticks along the left and bottom edges, like a map frame -->
	<div class="ticks-y absolute inset-y-0 left-0 -z-10 hidden w-3 lg:block" aria-hidden="true"></div>
	<div
		class="ticks-x absolute inset-x-0 bottom-0 -z-10 hidden h-3 lg:block"
		aria-hidden="true"
	></div>

	<div class="mx-auto flex h-full max-w-7xl flex-col justify-between px-6 pb-8 pt-14 lg:px-10">
		<div class="grid flex-1 items-center gap-12 lg:grid-cols-[1.15fr_1fr]">
			<!-- Headline -->
			<div class="max-w-2xl">
				<h1 class="headline">
					<span class="line" style="--l:0">{$t('home.where_next_1')}</span>
					<span class="line" style="--l:1">{$t('home.where_next_2')}</span>
				</h1>
				<p class="lede">{$t('home.welcome_line')}</p>
				<div class="mt-9 flex flex-wrap gap-3 cta">
					<button onclick={() => goto('/login')} class="btn btn-primary btn-lg rounded-full px-8">
						{$t('auth.login')}
						<ArrowRight class="h-5 w-5" />
					</button>
					<button
						onclick={() => goto('/signup')}
						class="btn btn-lg rounded-full border-white/30 bg-white/10 px-8 text-white backdrop-blur-md hover:bg-white/20"
					>
						{$t('auth.signup')}
					</button>
				</div>
			</div>

			<!-- Floating app cards -->
			<div class="cards relative hidden h-[30rem] lg:block" aria-hidden="true">
				<!-- Location card -->
				<div class="glass float-a absolute right-0 top-0 w-80 overflow-hidden rounded-3xl p-2">
					{#if background.url}
						<img src={background.url} alt="" class="h-44 w-full rounded-2xl object-cover" />
					{/if}
					<div class="space-y-2 p-3">
						<div class="flex items-center justify-between">
							<span
								class="flex items-center gap-1.5 rounded-full bg-success/90 px-2.5 py-0.5 text-xs font-semibold text-success-content"
							>
								<CheckCircle class="h-3.5 w-3.5" />
								{$t('adventures.visited')}
							</span>
							<span class="flex items-center gap-0.5 text-accent">
								{#each Array(5) as _}<Star class="h-4 w-4" />{/each}
							</span>
						</div>
						<p class="text-lg font-semibold leading-snug">
							{background.location ?? 'Your next favorite place'}
						</p>
					</div>
				</div>

				<!-- Itinerary card -->
				<div class="glass float-b absolute bottom-0 left-0 w-72 rounded-3xl p-4">
					<div class="mb-3 flex items-center gap-2 text-sm font-semibold">
						<CalendarOutline class="h-4 w-4 text-accent" />
						{$t('home.itinerary_title')}
					</div>
					<ul class="space-y-2.5">
						{#each days as day}
							<li class="flex items-center gap-3 text-sm">
								<span class="w-9 text-xs text-white/55">{day.d}</span>
								<span class="h-2 w-2 shrink-0 rounded-full {day.done ? 'bg-accent' : 'bg-white/30'}"
								></span>
								<span class={day.done ? 'text-white' : 'text-white/70'}>{day.name}</span>
							</li>
						{/each}
					</ul>
				</div>

				<!-- Stat chip -->
				<div class="glass float-c absolute bottom-24 right-6 rounded-2xl px-5 py-3">
					<p class="text-3xl font-bold leading-none tabular-nums">34</p>
					<p class="mt-1 text-xs text-white/65">{$t('home.countries_visited')}</p>
				</div>
			</div>
		</div>

		<!-- Photo credit -->
		{#if background.location}
			<p class="credit flex items-center gap-2 text-sm text-white/75">
				<MapMarker class="h-4 w-4 text-accent" />
				<span>{background.location}</span>
				{#if background.author}<span class="text-white/45">· {background.author}</span>{/if}
			</p>
		{/if}
	</div>
</section>

<svelte:head>
	<title>AdventureLog</title>
	<meta
		name="description"
		content="AdventureLog is a platform to log your adventures and plan your travel."
	/>
</svelte:head>

<style>
	.hero {
		min-height: calc(100svh - 4rem);
	}
	.hero-shade {
		background:
			linear-gradient(
				100deg,
				rgb(8 14 12 / 0.88) 0%,
				rgb(8 14 12 / 0.55) 45%,
				rgb(8 14 12 / 0.2) 100%
			),
			linear-gradient(0deg, rgb(8 14 12 / 0.7) 0%, transparent 35%);
	}

	/* Map overlay */
	.contours path {
		opacity: 0.1;
	}
	.contours path:nth-child(3n) {
		opacity: 0.18;
	}
	.route {
		stroke-linecap: round;
		stroke-dasharray: 1400;
		stroke-dashoffset: 1400;
		filter: drop-shadow(0 0 6px var(--color-accent));
	}
	.ready .route {
		animation: draw 2.6s cubic-bezier(0.5, 0, 0.2, 1) 0.5s forwards;
	}
	.pin {
		opacity: 0;
	}
	.ready .pin {
		animation: drop 0.6s cubic-bezier(0.3, 1.5, 0.5, 1) calc(0.6s + var(--d) * 0.55s) forwards;
	}
	.pin-ring {
		opacity: 0.25;
		transform-box: fill-box;
		transform-origin: center;
		animation: pulse 2.8s ease-out infinite;
	}
	@keyframes draw {
		to {
			stroke-dashoffset: 0;
		}
	}
	@keyframes drop {
		from {
			opacity: 0;
			transform: translate(var(--tx, 0), var(--ty, 0)) scale(0.2);
		}
		to {
			opacity: 1;
		}
	}
	@keyframes pulse {
		0% {
			transform: scale(0.6);
			opacity: 0.45;
		}
		100% {
			transform: scale(1.9);
			opacity: 0;
		}
	}

	/* Map-frame ticks */
	.ticks-y {
		background: repeating-linear-gradient(
			to bottom,
			rgb(255 255 255 / 0.35) 0 1px,
			transparent 1px 24px
		);
		mask-image: linear-gradient(to right, black 0 0);
	}
	.ticks-x {
		background: repeating-linear-gradient(
			to right,
			rgb(255 255 255 / 0.35) 0 1px,
			transparent 1px 24px
		);
	}

	/* Type */
	.headline {
		font-size: clamp(3.4rem, 9.5vw, 8.5rem);
		font-weight: 800;
		line-height: 0.92;
		letter-spacing: -0.045em;
	}
	.line {
		display: block;
		opacity: 0;
		transform: translateY(0.4em);
		filter: blur(8px);
	}
	.ready .line {
		animation: rise 1s cubic-bezier(0.2, 0.7, 0.2, 1) calc(0.15s + var(--l) * 0.16s) forwards;
	}
	@keyframes rise {
		to {
			opacity: 1;
			transform: none;
			filter: none;
		}
	}
	.lede {
		margin-top: 1.75rem;
		max-width: 30rem;
		font-size: 1.2rem;
		line-height: 1.55;
		color: rgb(255 255 255 / 0.78);
	}
	.lede,
	.cta,
	.credit,
	.cards {
		opacity: 0;
	}
	.ready .lede,
	.ready .cta,
	.ready .credit {
		animation: fade 0.9s ease-out 0.55s forwards;
	}
	.ready .cards {
		animation: fade 1.1s ease-out 1.1s forwards;
	}
	@keyframes fade {
		to {
			opacity: 1;
		}
	}

	/* Glass cards */
	.glass {
		background: rgb(14 22 20 / 0.5);
		border: 1px solid rgb(255 255 255 / 0.16);
		backdrop-filter: blur(18px) saturate(1.3);
		box-shadow: 0 24px 60px -20px rgb(0 0 0 / 0.6);
		color: white;
	}
	.float-a {
		transform: translate(calc(var(--px) * -18px), calc(var(--py) * -14px));
	}
	.float-b {
		transform: translate(calc(var(--px) * 26px), calc(var(--py) * 20px));
	}
	.float-c {
		transform: translate(calc(var(--px) * -34px), calc(var(--py) * 28px));
	}
	.float-a,
	.float-b,
	.float-c {
		transition: transform 0.5s cubic-bezier(0.2, 0.7, 0.2, 1);
	}

	@media (prefers-reduced-motion: reduce) {
		.line,
		.lede,
		.cta,
		.credit,
		.cards {
			transition: none;
			animation: none !important;
			opacity: 1;
			transform: none;
			filter: none;
		}
		.route {
			stroke-dashoffset: 0;
		}
		.pin {
			opacity: 1;
		}
		.pin-ring {
			animation: none;
		}
	}
</style>
