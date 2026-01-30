<script lang="ts">
	import { onMount } from 'svelte';
	import confetti from 'canvas-confetti';
	import LanguageBlock from './LanguageBlock.svelte';

	export let step: number;
	export let title_es: string;
	export let title_en: string;
	export let clue_es: string;
	export let clue_en: string;
	export let locationName: string;
	export let googleMapsUrl: string;
	export let photo: string;
	export let photoBlur: string;
	export let isUnlocked: boolean = false;
	export let onUnlock: () => void = () => {};

	let imageLoaded = false;
	let showConfetti = false;

	function handleUnlock() {
		showConfetti = true;
		onUnlock();

		// Trigger confetti
		if (typeof window !== 'undefined') {
			confetti({
				particleCount: 100,
				spread: 60,
				origin: { x: 0.5, y: 0.5 },
				colors: ['#e04d75', '#eab308', '#ffc0cb', '#fdf2f4']
			});
		}
	}

	function openMaps() {
		if (typeof window !== 'undefined') {
			window.open(googleMapsUrl, '_blank');
		}
	}

	onMount(() => {
		const img = new Image();
		img.onload = () => (imageLoaded = true);
		img.src = photo;
	});
</script>

<div class="max-w-2xl mx-auto px-4 py-8">
	<div
		class="rounded-3xl overflow-hidden shadow-lg transition-all duration-500"
		class:ring-2={isUnlocked}
		class:ring-amber-500={isUnlocked}
	>
		<!-- Image Container -->
		<div class="relative w-full aspect-video bg-stone-100 overflow-hidden">
			<img
				src={isUnlocked ? photo : photoBlur}
				alt={locationName}
				class="w-full h-full object-cover transition-all duration-700"
				class:blur-xl={!isUnlocked}
				class:blur-none={isUnlocked}
			/>

			<!-- Locked Overlay -->
			{#if !isUnlocked}
				<div
					class="absolute inset-0 bg-gradient-to-b from-black/60 to-black/85 flex items-center justify-center"
				>
					<div class="text-center">
						<div class="text-6xl mb-4">🔒</div>
						<p class="text-white font-semibold">Sorpresa bloqueada</p>
						<p class="text-white/70 text-sm">Locked</p>
					</div>
				</div>
			{/if}

			<!-- Progress Badge -->
			<div class="absolute top-4 right-4 bg-amber-50/95 px-3 py-2 rounded-full text-sm font-medium">
				<span class="text-amber-950">{step}</span>
				<span class="text-amber-600">/6</span>
			</div>
		</div>

		<!-- Content -->
		<div class="p-6 bg-gradient-to-b from-white to-amber-50/50">
			<!-- Title & Clue -->
			<div class="mb-6">
				<LanguageBlock
					spanish={title_es}
					english={title_en}
					spanishSize="text-2xl md:text-3xl"
					englishSize="text-xs md:text-sm"
				/>
			</div>

			<!-- Clue Text -->
			{#if isUnlocked}
				<div
					class="mb-6 p-4 bg-amber-50 rounded-lg border border-amber-100 transition-all duration-500"
				>
					<p class="text-stone-900 font-body text-sm md:text-base mb-3">{clue_es}</p>
					<p class="text-stone-600 font-body text-xs md:text-sm">{clue_en}</p>
				</div>
			{/if}

			<!-- Buttons -->
			<div class="flex flex-col gap-3">
				{#if !isUnlocked}
					<button
						on:click={handleUnlock}
						class="w-full py-3 px-4 bg-gradient-to-r from-amber-400 to-amber-300 text-amber-950 font-semibold rounded-full hover:shadow-lg hover:scale-105 transition-all duration-200 active:scale-95"
					>
						✨ Siguiente sorpresa / Next Surprise
					</button>
				{:else}
					<button
						on:click={openMaps}
						class="w-full py-3 px-4 bg-gradient-to-r from-rose-400 to-rose-300 text-white font-semibold rounded-full hover:shadow-lg hover:scale-105 transition-all duration-200 active:scale-95 flex items-center justify-center gap-2"
					>
						<span>📍</span>
						<span>Navegar / Navigate to {locationName}</span>
					</button>
				{/if}
			</div>
		</div>
	</div>
</div>

<style>
	:global(.font-display) {
		font-family: 'Playfair Display', Georgia, serif;
	}
	:global(.font-body) {
		font-family:
			'Inter',
			-apple-system,
			BlinkMacSystemFont,
			'Segoe UI',
			sans-serif;
	}
</style>
