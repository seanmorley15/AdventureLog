<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { onMount } from 'svelte';
	import { fade, scale } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';
	import { t } from 'svelte-i18n';

	// Icons
	import AlertTriangle from '~icons/mdi/alert';
	import HelpCircle from '~icons/mdi/help-circle';
	import InfoCircle from '~icons/mdi/information';
	import Close from '~icons/mdi/close';
	import Check from '~icons/mdi/check';
	import Cancel from '~icons/mdi/cancel';

	const dispatch = createEventDispatcher();

	let modal: HTMLDialogElement;
	let isVisible = false;

	export let title: string;
	export let button_text: string;
	export let description: string;
	export let is_warning: boolean = false;

	$: modalType = is_warning ? 'warning' : 'info';
	$: iconComponent = is_warning ? AlertTriangle : HelpCircle;
	$: colorScheme = getColorScheme(modalType);

	function getColorScheme(type: string) {
		switch (type) {
			case 'warning':
				return {
					icon: 'text-warning',
					iconBg: 'bg-warning/10',
					border: 'border-warning/20',
					button: 'btn-warning',
					backdrop: 'bg-warning/5'
				};
			default:
				return {
					icon: 'text-info',
					iconBg: 'bg-info/10',
					border: 'border-info/20',
					button: 'btn-primary',
					backdrop: 'bg-info/5'
				};
		}
	}

	onMount(() => {
		modal = document.getElementById('confirmation_modal') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
			setTimeout(() => (isVisible = true), 50);
		}
	});

	function close() {
		isVisible = false;
		setTimeout(() => {
			modal?.close();
			dispatch('close');
		}, 150);
	}

	function confirm() {
		isVisible = false;
		setTimeout(() => {
			modal?.close();
			dispatch('close');
			dispatch('confirm');
		}, 150);
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			close();
		}
	}

	function handleBackdropClick(event: MouseEvent) {
		if (event.target === modal) {
			close();
		}
	}
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
<dialog
	id="confirmation_modal"
	class="modal backdrop-blur-sm"
	on:click={handleBackdropClick}
	on:keydown={handleKeydown}
>
	{#if isVisible}
		<div
			class="modal-box max-w-md relative overflow-hidden border-2 {colorScheme.border} bg-base-100/95 backdrop-blur-lg shadow-2xl"
			transition:scale={{ duration: 150, easing: quintOut, start: 0.1 }}
			role="dialog"
			aria-labelledby="modal-title"
			aria-describedby="modal-description"
		>
			<!-- Close button -->
			<button
				class="btn btn-sm btn-circle btn-ghost absolute right-4 top-4 hover:bg-base-content/10 transition-colors"
				on:click={close}
				aria-label="Close modal"
			>
				<Close class="w-4 h-4" />
			</button>

			<!-- Content -->
			<div class="flex flex-col items-center text-center pt-6 pb-2">
				<!-- Icon -->
				<div
					class="w-16 h-16 rounded-full {colorScheme.iconBg} flex items-center justify-center mb-6 ring-4 ring-base-300/20"
				>
					<svelte:component this={iconComponent} class="w-8 h-8 {colorScheme.icon}" />
				</div>

				<!-- Title -->
				<h3 id="modal-title" class="text-2xl font-bold text-base-content mb-3">
					{title}
				</h3>

				<!-- Description -->
				<p id="modal-description" class="text-base-content/70 leading-relaxed mb-8 max-w-sm">
					{description}
				</p>
			</div>

			<!-- Action Buttons -->
			<div class="flex flex-col sm:flex-row gap-3 sm:gap-4">
				<button
					class="btn {colorScheme.button} flex-1 gap-2 shadow-lg hover:shadow-xl transition-all duration-200"
					on:click={confirm}
				>
					<Check class="w-4 h-4" />
					{button_text}
				</button>
				<button
					class="btn btn-neutral-200 flex-1 gap-2 hover:bg-base-content/10 transition-colors"
					on:click={close}
				>
					<Cancel class="w-4 h-4" />
					{$t('adventures.cancel')}
				</button>
			</div>

			<!-- Subtle gradient overlay for depth -->
			<div
				class="absolute inset-0 bg-gradient-to-br from-white/5 via-transparent to-black/5 pointer-events-none"
			></div>

			<!-- Decorative elements -->
			<div
				class="absolute -top-20 -right-20 w-40 h-40 {colorScheme.iconBg} rounded-full opacity-20 blur-3xl"
			></div>
			<div
				class="absolute -bottom-10 -left-10 w-32 h-32 {colorScheme.iconBg} rounded-full opacity-10 blur-2xl"
			></div>
		</div>

		<!-- Enhanced backdrop -->
		<div
			class="fixed inset-0 {colorScheme.backdrop} -z-10"
			transition:fade={{ duration: 200 }}
		></div>
	{/if}
</dialog>

<style>
	/* Ensure modal appears above everything */
	dialog {
		z-index: 9999;
	}

	/* Custom backdrop blur effect */
	dialog::backdrop {
		backdrop-filter: blur(8px);
		background: rgba(0, 0, 0, 0.3);
	}

	/* Smooth modal entrance */
	.modal-box {
		transform-origin: center;
	}

	/* Enhanced button hover effects */
	.btn:hover {
		transform: translateY(-1px);
	}

	/* Focus styles for accessibility */
	.btn:focus-visible {
		outline: 2px solid currentColor;
		outline-offset: 2px;
	}
</style>
