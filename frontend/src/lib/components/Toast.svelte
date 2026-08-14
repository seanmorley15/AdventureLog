<script lang="ts">
	import { toasts, removeToast } from '$lib/toasts';
	import { onMount } from 'svelte';

	let toastList: any[] = $state([]);

	toasts.subscribe((value) => {
		toastList = value;
	});

	function getIconSvg(type: string) {
		switch (type) {
			case 'success':
				return `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"></path></svg>`;
			case 'error':
				return `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12"></path></svg>`;
			case 'warning':
				return `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>`;
			case 'info':
				return `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`;
			default:
				return `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`;
		}
	}
</script>

<div class="toast toast-top toast-end z-[9999] mt-16 gap-3 max-w-md px-4">
	{#each toastList as { type, message, id }}
		<div
			class="alert alert-{type} shadow-2xl backdrop-blur-sm rounded-2xl border-0 min-w-80 max-w-md animate-in slide-in-from-right-5 fade-in duration-300"
			role="alert"
		>
			<div class="flex items-center gap-4 w-full py-1">
				<!-- Icon -->
				<div
					class="flex-shrink-0 w-10 h-10 rounded-full bg-base-100/20 flex items-center justify-center"
				>
					{@html getIconSvg(type)}
				</div>

				<!-- Message -->
				<div class="flex-1 min-w-0">
					<p class="text-sm font-medium leading-relaxed break-words">{message}</p>
				</div>

				<!-- Close Button -->
				<button
					class="btn btn-ghost btn-sm btn-circle opacity-70 hover:opacity-100 transition-opacity flex-shrink-0 -mr-1"
					onclick={() => removeToast(id)}
					aria-label="Close notification"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2.5"
							d="M6 18L18 6M6 6l12 12"
						></path>
					</svg>
				</button>
			</div>
		</div>
	{/each}
</div>

<style>
	@keyframes slide-in-from-right-5 {
		from {
			transform: translateX(1.25rem);
		}
		to {
			transform: translateX(0);
		}
	}

	@keyframes fade-in {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}

	.animate-in {
		animation:
			slide-in-from-right-5 0.3s ease-out,
			fade-in 0.3s ease-out;
	}
</style>
