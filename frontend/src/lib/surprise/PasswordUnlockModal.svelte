<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { fly } from 'svelte/transition';

	export let isOpen = false;
	export let stepNumber = 1;
	export let correctPassword = '';

	const dispatch = createEventDispatcher();

	let input = '';
	let isWrong = false;
	let attempts = 0;

	function handleSubmit() {
		attempts++;
		if (input.toUpperCase() === correctPassword.toUpperCase()) {
			dispatch('unlocked');
			input = '';
			isWrong = false;
			attempts = 0;
		} else {
			isWrong = true;
			input = '';
			setTimeout(() => (isWrong = false), 500);
		}
	}

	function handleClose() {
		input = '';
		isWrong = false;
		dispatch('close');
	}
</script>

{#if isOpen}
	<div
		class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
		on:click={handleClose}
		on:keydown={(e) => e.key === 'Escape' && handleClose()}
		role="button"
		tabindex="-1"
		aria-label="Close modal"
	>
		<div
			class="bg-white rounded-2xl p-8 max-w-sm w-full mx-4 shadow-2xl"
			on:click|stopPropagation
			transition:fly={{ y: 20 }}
		>
			<div class="text-center">
				<div class="text-5xl mb-4">🔐</div>
				<h2 class="text-xl font-bold mb-2 text-gray-800">Unlock Step {stepNumber}</h2>
				<p class="text-sm text-gray-600 mb-6">Enter the password to reveal this surprise</p>
			</div>

			<form on:submit|preventDefault={handleSubmit} class="space-y-4">
				<div>
					<input
						type="password"
						bind:value={input}
						placeholder="Enter password..."
						class={`w-full px-4 py-3 rounded-lg border-2 transition-all focus:outline-none ${
							isWrong ? 'border-red-500 bg-red-50 shake' : 'border-gray-300 focus:border-blue-500'
						}`}
						autocomplete="off"
					/>
					{#if isWrong}
						<p class="text-red-500 text-sm mt-2 text-center font-semibold">
							❌ Wrong password (Attempt {attempts})
						</p>
					{/if}
				</div>

				<div class="flex gap-3">
					<button
						type="button"
						on:click={handleClose}
						class="flex-1 px-4 py-2 rounded-lg bg-gray-200 text-gray-800 font-medium hover:bg-gray-300 transition"
					>
						Cancel
					</button>
					<button
						type="submit"
						class="flex-1 px-4 py-2 rounded-lg bg-gradient-to-r from-purple-500 to-pink-500 text-white font-medium hover:shadow-lg transition"
					>
						Unlock
					</button>
				</div>
			</form>

			{#if attempts > 2}
				<p class="text-xs text-gray-500 text-center mt-4">💡 Hint: Think about this step's theme</p>
			{/if}
		</div>
	</div>
{/if}

<style>
	@keyframes shake {
		0%,
		100% {
			transform: translateX(0);
		}
		25% {
			transform: translateX(-5px);
		}
		75% {
			transform: translateX(5px);
		}
	}

	.shake {
		animation: shake 0.3s;
	}
</style>
