<script lang="ts">
	import confetti from 'canvas-confetti';
	import { fly, fade } from 'svelte/transition';
	import PasswordUnlockModal from './PasswordUnlockModal.svelte';

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
	export let password: string;
	export let isUnlocked: boolean = false;
	export let onUnlock: () => void = () => {};

	let showPasswordModal = false;
	let imageError = false;

	function handleUnlockClick() {
		showPasswordModal = true;
	}

	function handlePasswordUnlocked() {
		showPasswordModal = false;
		onUnlock();

		// Trigger confetti
		if (typeof window !== 'undefined') {
			confetti({
				particleCount: 150,
				spread: 70,
				origin: { x: 0.5, y: 0.5 },
				colors: ['#9333ea', '#ec4899', '#8b5cf6', '#f472b6'],
				gravity: 0.8,
				ticks: 80
			});
		}
	}
</script>

<div
	class="card bg-gradient-to-br from-white to-gray-50 shadow-xl rounded-2xl overflow-hidden hover:shadow-2xl transition-all"
	transition:fly={{ y: 20, duration: 500 }}
>
	<!-- Image Container -->
	<div
		class="relative w-full h-80 md:h-96 overflow-hidden bg-gradient-to-br from-blue-400 via-purple-400 to-pink-400"
	>
		{#if isUnlocked}
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
		{:else}
			<!-- Locked State -->
			<img src={photoBlur} alt="Locked" class="w-full h-full object-cover filter blur-xl" />
			<div
				class="absolute inset-0 bg-gradient-to-t from-black/60 via-black/30 to-transparent flex items-center justify-center backdrop-blur-sm"
			>
				<div class="text-center">
					<div class="text-7xl mb-3 animate-pulse">🔒</div>
					<p class="text-white font-bold text-lg">Surprise Locked</p>
					<p class="text-white/90 text-sm">Password required to reveal</p>
				</div>
			</div>
		{/if}
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
			{#if isUnlocked}
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

		<!-- Content Display -->
		{#if isUnlocked}
			<!-- Unlocked Content -->
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

			<!-- Continue Button -->
			<button
				disabled
				class="w-full bg-gradient-to-r from-green-500 to-emerald-500 text-white font-bold py-3 rounded-lg shadow-lg cursor-default hover:shadow-xl transition-all"
			>
				✅ Step Unlocked!
			</button>
		{:else}
			<!-- Locked Content -->
			<div class="mb-6">
				<p class="text-gray-700 font-semibold leading-relaxed mb-3">{clue_es}</p>
				<p class="text-gray-500 text-sm italic">{clue_en}</p>
			</div>

			<!-- Unlock Button -->
			<button
				on:click={handleUnlockClick}
				class="w-full bg-gradient-to-r from-purple-500 via-pink-500 to-red-500 text-white font-bold py-4 rounded-lg shadow-lg hover:shadow-xl transition-all hover:scale-105 active:scale-95 text-lg"
			>
				🔐 Unlock Surprise #{step}
			</button>
		{/if}
	</div>
</div>

<!-- Password Modal -->
<PasswordUnlockModal
	isOpen={showPasswordModal}
	stepNumber={step}
	correctPassword={password}
	on:unlocked={handlePasswordUnlocked}
	on:close={() => (showPasswordModal = false)}
/>

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
