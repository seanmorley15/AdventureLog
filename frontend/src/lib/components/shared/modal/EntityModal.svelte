<script lang="ts">
	/**
	 * EntityModal - Reusable modal wrapper for entity editing (Location, Transportation, Lodging)
	 *
	 * Provides:
	 * - Modal dialog with standard styling
	 * - Header with icon, title, step timeline, close button
	 * - Escape key handling
	 * - Close event dispatching with save state tracking
	 */
	import { createEventDispatcher, onMount } from 'svelte';
	import type { ModalStep } from './types';
	import EntityModalHeader from './EntityModalHeader.svelte';
	import { navigateToStep } from './types';

	// Props
	export let modalId: string = 'entity_modal';
	export let icon: any = null;
	export let title: string;
	export let subtitle: string;
	export let steps: ModalStep[];
	export let entityId: string;
	export let didSave: boolean = false;
	export let isEditing: boolean = false;

	const dispatch = createEventDispatcher();

	let modal: HTMLDialogElement;

	onMount(() => {
		modal?.showModal();
	});

	export function close() {
		if (didSave) {
			dispatch(isEditing ? 'save' : 'create');
		}
		dispatch('close');
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			event.preventDefault(); // Prevent native dialog close (we handle it ourselves)
			close();
		}
	}

	function handleStepClick(e: CustomEvent<{ index: number }>) {
		steps = navigateToStep(steps, e.detail.index);
		dispatch('stepsChange', steps);
	}
</script>

<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
<dialog bind:this={modal} id={modalId} class="modal backdrop-blur-sm" on:cancel|preventDefault>
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div
		class="modal-box w-11/12 max-w-6xl bg-gradient-to-br from-base-100 via-base-100 to-base-200 border border-base-300 shadow-2xl"
		role="dialog"
		on:keydown={handleKeydown}
		tabindex="0"
	>
		<EntityModalHeader
			{icon}
			{title}
			{subtitle}
			{steps}
			{entityId}
			on:stepClick={handleStepClick}
			on:close={() => close()}
		>
			<slot name="icon" slot="icon" />
		</EntityModalHeader>

		<slot />
	</div>
</dialog>
