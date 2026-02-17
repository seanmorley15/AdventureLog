<script lang="ts">
	/**
	 * Pagination - Shared pagination component for list pages
	 */
	import { createEventDispatcher } from 'svelte';

	export let currentPage: number = 1;
	export let totalPages: number = 1;

	const dispatch = createEventDispatcher<{ changePage: number }>();

	function handlePageChange(page: number) {
		dispatch('changePage', page);
	}
</script>

{#if totalPages > 1}
	<div class="flex justify-center mt-12">
		<div class="join bg-base-100 shadow-lg rounded-2xl p-2">
			{#each Array.from({ length: totalPages }, (_, i) => i + 1) as page}
				<button
					class="join-item btn btn-sm {currentPage === page ? 'btn-primary' : 'btn-ghost'}"
					on:click={() => handlePageChange(page)}
				>
					{page}
				</button>
			{/each}
		</div>
	</div>
{/if}
