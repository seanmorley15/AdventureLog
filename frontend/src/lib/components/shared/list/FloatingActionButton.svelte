<script lang="ts">
	/**
	 * FloatingActionButton - FAB for creating new entities
	 */
	import { createEventDispatcher } from 'svelte';
	import Plus from '~icons/mdi/plus';

	const dispatch = createEventDispatcher<{ click: void }>();
</script>

<div class="fixed bottom-6 right-6 z-[999]">
	<button
		class="btn btn-primary btn-circle w-16 h-16 shadow-2xl hover:shadow-primary/25 transition-all duration-200"
		on:click={() => dispatch('click')}
	>
		<Plus class="w-8 h-8" />
	</button>
</div>
