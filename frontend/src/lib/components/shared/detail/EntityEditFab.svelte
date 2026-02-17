<script lang="ts">
	import ClipboardList from '~icons/mdi/clipboard-list';

	export let show: boolean = true;
	export let onClick: () => void;
</script>

{#if show}
	<div class="fixed bottom-6 right-6 z-50">
		<button
			class="btn btn-primary btn-circle w-16 h-16 shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-110"
			on:click={onClick}
		>
			<ClipboardList class="w-8 h-8" />
		</button>
	</div>
{/if}
