<script lang="ts">
	import { onMount } from 'svelte';
	import StepCard from './StepCard.svelte';
	import useSurpriseProgress from './useSurpriseProgress';
	import type { Step } from './types';

	let steps: Step[] = [];
	let unlockedSteps: Set<number> = new Set();
	let loading = true;
	let error: string | null = null;

	const { getProgress, saveProgress } = useSurpriseProgress();

	onMount(async () => {
		try {
			const response = await fetch('/surprise/itinerary/yvette-cuernavaca.json');
			if (!response.ok) throw new Error('Failed to load itinerary');
			steps = await response.json();

			// Load previously unlocked steps
			const savedProgress = getProgress();
			unlockedSteps = new Set(savedProgress);

			loading = false;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Unknown error';
			loading = false;
		}
	});

	function handleStepUnlock(stepNum: number) {
		unlockedSteps = new Set([...unlockedSteps, stepNum]);
		saveProgress(Array.from(unlockedSteps));
	}
</script>

<div class="min-h-screen bg-gradient-to-br from-purple-50 via-white to-pink-50">
	<!-- Header -->
	<div class="sticky top-0 z-40 bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-lg">
		<div class="max-w-6xl mx-auto px-4 py-6 text-center">
			<h1 class="text-4xl font-black mb-2">✨ Sorpresa en Cuernavaca ✨</h1>
			<p class="text-purple-100">A treasure hunt of love and discovery</p>
		</div>
	</div>

	<!-- Progress Bar -->
	<div class="bg-gradient-to-r from-purple-100 to-pink-100 border-b border-purple-200">
		<div class="max-w-6xl mx-auto px-4 py-4">
			<div class="flex items-center justify-between text-sm font-semibold mb-2">
				<span class="text-gray-700">Your Progress:</span>
				<span class="text-purple-600">{unlockedSteps.size} of {steps.length} Unlocked</span>
			</div>
			<div class="w-full bg-white rounded-full h-3 shadow-inner overflow-hidden">
				<div
					class="bg-gradient-to-r from-purple-500 to-pink-500 h-full transition-all duration-300"
					style="width: {steps.length > 0 ? (unlockedSteps.size / steps.length) * 100 : 0}%;"
				/>
			</div>
		</div>
	</div>

	<!-- Main Content -->
	<div class="max-w-6xl mx-auto px-4 py-12">
		{#if loading}
			<div class="flex items-center justify-center min-h-96">
				<div class="text-center">
					<div class="text-6xl mb-4 animate-spin">🎁</div>
					<p class="text-gray-600 text-lg font-semibold">Loading your surprises...</p>
				</div>
			</div>
		{:else if error}
			<div class="bg-red-100 border border-red-400 text-red-700 px-6 py-4 rounded-lg text-center">
				<p class="font-semibold">😞 Error loading surprises</p>
				<p class="text-sm">{error}</p>
			</div>
		{:else}
			<div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
				{#each steps as step (step.step)}
					<StepCard
						step={step.step}
						title_es={step.title_es}
						title_en={step.title_en}
						clue_es={step.clue_es}
						clue_en={step.clue_en}
						description_es={step.description_es}
						description_en={step.description_en}
						locationName={step.locationName}
						googleMapsUrl={step.googleMapsUrl}
						photo={step.photo}
						photoBlur={step.photoBlur}
						password={step.password}
						isUnlocked={unlockedSteps.has(step.step)}
						onUnlock={() => handleStepUnlock(step.step)}
					/>
				{/each}
			</div>

			<!-- Completion Message -->
			{#if unlockedSteps.size === steps.length}
				<div
					class="mt-12 bg-gradient-to-r from-yellow-100 to-orange-100 border-2 border-yellow-400 rounded-2xl p-8 text-center shadow-xl"
				>
					<div class="text-6xl mb-4 animate-bounce">🎊</div>
					<h2 class="text-3xl font-black text-yellow-800 mb-2">¡Lo hicimos! We Did It!</h2>
					<p class="text-yellow-700 text-lg mb-4">
						All of Yvette's surprises have been revealed. Get ready for an unforgettable adventure!
						🚀
					</p>
					<a
						href="/"
						class="inline-block bg-gradient-to-r from-yellow-500 to-orange-500 text-white font-bold px-8 py-3 rounded-lg hover:shadow-lg transition-all"
					>
						Back to Home
					</a>
				</div>
			{/if}
		{/if}
	</div>

	<!-- Footer -->
	<div class="bg-gradient-to-r from-purple-900 to-pink-900 text-white text-center py-8 mt-12">
		<p class="text-sm">Made with 💜 by Kupuri Studios</p>
		<p class="text-xs text-purple-300 mt-2">For Yvette's Cuernavaca Adventure</p>
	</div>
</div>

<style>
	:global(body) {
		@apply bg-gradient-to-br from-purple-50 via-white to-pink-50;
	}
</style>
