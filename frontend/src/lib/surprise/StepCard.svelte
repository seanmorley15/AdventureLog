<script lang="ts">
	import confetti from 'canvas-confetti';
	import { fly, fade } from 'svelte/transition';
	import { onMount } from 'svelte';

	export let step: number;
	export let title_es: string;
	export let title_en: string;
	export let clue_es: string;
	export let clue_en: string;
	export let description_es: string;
	export let description_en: string;
	export let locationName: string;
	export let googleMapsUrl: string;
	export let photo: string;
	export let photoBlur: string;
	export let isViewed: boolean = false;
	export let onView: () => void = () => {};

	let imageError = false;
	let cardElement: HTMLElement;
	let hasTriggeredConfetti = false;

	onMount(() => {
		// Create an intersection observer to trigger confetti when card comes into view
		const observer = new IntersectionObserver(
			(entries) => {
				entries.forEach((entry) => {
					if (entry.isIntersecting && !hasTriggeredConfetti && !isViewed) {
						// Trigger confetti when card is viewed for the first time
						hasTriggeredConfetti = true;
						onView();
						triggerConfetti();
					}
				});
			},
			{ threshold: 0.5 }
		);

		if (cardElement) {
			observer.observe(cardElement);
		}

		return () => {
			if (cardElement) {
				observer.unobserve(cardElement);
			}
		};
	});

	function triggerConfetti() {
		if (typeof window !== 'undefined') {
			confetti({
				particleCount: 100,
				spread: 60,
				origin: { x: 0.5, y: 0.6 },
				colors: ['#9333ea', '#ec4899', '#8b5cf6', '#f472b6'],
				gravity: 0.8,
				ticks: 60
			});
		}
	}
</script>

<div
	bind:this={cardElement}
	class="card bg-gradient-to-br from-white to-gray-50 shadow-xl rounded-2xl overflow-hidden hover:shadow-2xl transition-all"
	transition:fly={{ y: 20, duration: 500 }}
>
	<!-- Image Container -->
	<div
		class="relative w-full h-80 md:h-96 overflow-hidden bg-gradient-to-br from-blue-400 via-purple-400 to-pink-400"
	>
		{#if imageError}
			<!-- Fallback gradient when image fails to load -->
			<div class="w-full h-full bg-gradient-to-br from-purple-400 via-pink-400 to-orange-400 flex items-center justify-center">
				<div class="text-center text-white">
					<div class="text-6xl mb-2">🏞️</div>
					<p class="font-bold">{title_es}</p>
				</div>
			</div>
		{:else}
			<img
				src={photo}
				alt={title_en}
				class="w-full h-full object-cover"
				transition:fade={{ duration: 400 }}
				on:error={() => (imageError = true)}
			/>
		{/if}
		<a
			href={googleMapsUrl}
			target="_blank"
			rel="noopener noreferrer"
			class="absolute top-4 right-4 bg-white/95 hover:bg-white px-4 py-2 rounded-full text-sm font-bold text-blue-600 shadow-lg transition-all hover:shadow-xl hover:scale-110"
		>
			📍 Navigate
		</a>
	</div>

	<!-- Content -->
	<div class="p-6 md:p-8">
		<!-- Progress Indicator -->
		<div class="flex items-center justify-between mb-4">
			<div
				class="inline-block bg-gradient-to-r from-purple-500 to-pink-500 text-white px-4 py-2 rounded-full text-sm font-bold shadow-lg"
			>
				Step {step} of 6 ✨
			</div>
			{#if isViewed}
				<span class="text-3xl animate-bounce">🎉</span>
			{/if}
		</div>

		<!-- Bilingual Title -->
		<div class="mb-6">
			<h2
				class="text-3xl font-black text-transparent bg-clip-text bg-gradient-to-r from-purple-600 to-pink-600 mb-2"
			>
				{title_es}
			</h2>
			<p class="text-sm text-gray-500 italic font-medium">{title_en}</p>
		</div>

		<!-- Content Display (Always Visible) -->
		<div class="mb-6 space-y-3 animate-fadeIn">
			<div class="border-l-4 border-purple-500 pl-4">
				<p class="text-gray-800 font-semibold leading-relaxed">{clue_es}</p>
				<p class="text-gray-500 text-sm italic mt-2">{clue_en}</p>
			</div>

			<div
				class="bg-gradient-to-r from-blue-50 to-purple-50 p-4 rounded-xl border border-blue-200"
			>
				<p class="text-gray-700 text-sm leading-relaxed">{description_es}</p>
				<p class="text-gray-500 text-xs italic mt-2">{description_en}</p>
			</div>

			<!-- Location Badge -->
			<div
				class="bg-gradient-to-r from-green-50 to-emerald-50 p-4 rounded-xl border border-green-200"
			>
				<p class="text-sm font-bold text-green-700">📍 {locationName}</p>
			</div>
		</div>

		<!-- Action Button -->
		<a
			href={googleMapsUrl}
			target="_blank"
			rel="noopener noreferrer"
			class="block w-full bg-gradient-to-r from-blue-500 to-purple-500 text-white font-bold py-4 rounded-lg shadow-lg hover:shadow-xl transition-all hover:scale-105 active:scale-95 text-center text-lg"
		>
			🗺️ Open in Maps
		</a>
	</div>
</div>

<style>
	@keyframes fadeIn {
		from {
			opacity: 0;
			transform: translateY(10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	:global(.animate-fadeIn) {
		animation: fadeIn 0.5s ease-out;
	}
</style>
