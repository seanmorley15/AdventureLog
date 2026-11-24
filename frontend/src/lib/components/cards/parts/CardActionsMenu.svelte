<script lang="ts">
	import { onMount, type Snippet } from 'svelte';
	import DotsHorizontal from '~icons/mdi/dots-horizontal';
	import { shouldFlipDropdownUp } from '#lib/utils/flipDropdown.js';

	interface Props {
		/** Accessible name for the trigger button. */
		label: string;
		/** Keeps the menu open (e.g. while an item inside it is loading). */
		busy?: boolean;
		/** Menu items. Call `close()` from an item to dismiss the menu. */
		children: Snippet<[{ close: () => void }]>;
	}

	let { label, busy = false, children }: Props = $props();

	// One shared event so opening a menu on one card closes the others.
	const CLOSE_EVENT = 'card-actions-close';

	let open = $state(false);
	let openUpward = $state(false);
	let root: HTMLDivElement | null = $state(null);
	let wasBusy = false;

	function close() {
		if (busy) return;
		open = false;
	}

	function toggle(event: MouseEvent) {
		event.stopPropagation();
		if (busy) return;
		if (open) {
			open = false;
			return;
		}
		window.dispatchEvent(new CustomEvent(CLOSE_EVENT));
		openUpward = shouldFlipDropdownUp(root);
		open = true;
	}

	function handleDocumentClick(event: MouseEvent) {
		if (!open || busy) return;
		const target = event.target as Node | null;
		if (root && target && !root.contains(target)) open = false;
	}

	onMount(() => {
		document.addEventListener('click', handleDocumentClick);
		window.addEventListener(CLOSE_EVENT, close);
		return () => {
			document.removeEventListener('click', handleDocumentClick);
			window.removeEventListener(CLOSE_EVENT, close);
		};
	});

	$effect(() => {
		if (busy) {
			open = true;
			wasBusy = true;
		} else if (wasBusy) {
			open = false;
			wasBusy = false;
		}
	});
</script>

<div
	class="dropdown dropdown-end relative z-30"
	class:dropdown-open={open}
	class:dropdown-top={openUpward}
	bind:this={root}
>
	<button
		type="button"
		class="btn btn-ghost btn-square btn-sm"
		aria-haspopup="menu"
		aria-expanded={open}
		aria-label={label}
		onclick={toggle}
	>
		<DotsHorizontal class="h-5 w-5" />
	</button>
	<ul
		tabindex="-1"
		class="dropdown-content menu z-[9999] max-h-[min(24rem,calc(100vh-2rem))] w-56 overflow-y-auto rounded-box border border-base-300 bg-base-100 p-2 shadow-lg"
	>
		{@render children({ close })}
	</ul>
</div>
