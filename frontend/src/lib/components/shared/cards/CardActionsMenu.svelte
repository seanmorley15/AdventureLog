<script lang="ts">
	/**
	 * CardActionsMenu - Shared dropdown menu for entity cards
	 * Handles the ACTIONS_CLOSE_EVENT pattern and menu state
	 */
	import { createEventDispatcher, onMount } from 'svelte';
	import DotsHorizontal from '~icons/mdi/dots-horizontal';

	export let ariaLabel: string = 'Actions';

	const dispatch = createEventDispatcher();

	let isOpen = false;
	let menuRef: HTMLDivElement | null = null;
	const ACTIONS_CLOSE_EVENT = 'card-actions-close';

	const handleCloseEvent = () => (isOpen = false);

	function handleDocumentClick(event: MouseEvent) {
		if (!isOpen) return;
		const target = event.target as Node | null;
		if (menuRef && target && !menuRef.contains(target)) {
			isOpen = false;
		}
	}

	function closeAllMenus() {
		window.dispatchEvent(new CustomEvent(ACTIONS_CLOSE_EVENT));
	}

	function toggleMenu() {
		if (isOpen) {
			isOpen = false;
			return;
		}
		closeAllMenus();
		isOpen = true;
	}

	export function close() {
		isOpen = false;
	}

	onMount(() => {
		document.addEventListener('click', handleDocumentClick);
		window.addEventListener(ACTIONS_CLOSE_EVENT, handleCloseEvent);
		return () => {
			document.removeEventListener('click', handleDocumentClick);
			window.removeEventListener(ACTIONS_CLOSE_EVENT, handleCloseEvent);
		};
	});
</script>

<div
	class="dropdown dropdown-end relative z-50"
	class:dropdown-open={isOpen}
	bind:this={menuRef}
>
	<button
		type="button"
		class="btn btn-square btn-sm p-1 text-base-content"
		aria-haspopup="menu"
		aria-label={ariaLabel}
		on:click|stopPropagation={toggleMenu}
	>
		<DotsHorizontal class="w-5 h-5" />
	</button>
	<ul
		tabindex="-1"
		class="dropdown-content menu bg-base-100 rounded-box z-[9999] w-52 p-2 shadow-lg border border-base-300"
	>
		<slot {close} />
	</ul>
</div>
