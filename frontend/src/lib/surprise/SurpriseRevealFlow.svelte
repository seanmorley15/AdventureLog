<script lang="ts">
	import { onMount } from 'svelte';
	import StepCard from './StepCard.svelte';
	import { useSurpriseProgress } from './useSurpriseProgress';
	import itinerary from './itinerary/yvette-cuernavaca.json';

	const { getProgress, advanceProgress } = useSurpriseProgress();
	let currentStep = 0;

	onMount(() => {
		currentStep = getProgress();
	});

	function handleUnlock() {
		currentStep = advanceProgress();
	}
</script>

<div class="min-h-screen bg-gradient-to-br from-amber-50 via-white to-rose-50 py-12">
	<div class="max-w-2xl mx-auto">
		<!-- Header -->
		<div class="text-center mb-12 px-4">
			<h1 class="font-display text-4xl md:text-5xl font-bold text-amber-950 mb-3">Yvette Milo</h1>
			<p class="font-body text-stone-600 text-lg">Sorpresa en Cuernavaca</p>
			<p class="font-body text-stone-500 text-sm mt-2">A treasure hunt of love</p>
		</div>

		<!-- Steps -->
		<div class="space-y-12 px-4 pb-12">
			{#each itinerary as step (step.step)}
				<StepCard
					step={step.step}
					title_es={step.title_es}
					title_en={step.title_en}
					clue_es={step.clue_es}
					clue_en={step.clue_en}
					locationName={step.locationName}
					googleMapsUrl={step.googleMapsUrl}
					photo={step.photo}
					photoBlur={step.photoBlur}
					isUnlocked={currentStep >= step.step}
					onUnlock={handleUnlock}
				/>
			{/each}
		</div>

		<!-- Completion Message -->
		{#if currentStep === 6}
			<div class="text-center px-4 mb-12 animate-pulse">
				<h2 class="font-display text-3xl font-bold text-rose-600 mb-3">
					¡Lo hicimos! / We Did It! 🎉
				</h2>
				<p class="font-body text-stone-600">Gracias por este viaje increíble contigo.</p>
				<p class="font-body text-stone-500 text-sm">
					Thank you for this incredible journey with you.
				</p>
			</div>
		{/if}
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
	:global(.animate-pulse) {
		animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
	}
	@keyframes pulse {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.5;
		}
	}
</style>
