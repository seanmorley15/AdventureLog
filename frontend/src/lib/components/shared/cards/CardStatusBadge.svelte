<script lang="ts">
	/**
	 * CardStatusBadge - Visited/not visited status indicator for entity cards
	 */
	import { t } from 'svelte-i18n';
	import Calendar from '~icons/mdi/calendar';
	import Clock from '~icons/mdi/clock-outline';

	export let isVisited: boolean = false;
</script>

<div class="absolute top-2 left-4 flex items-center gap-3">
	<div
		class="tooltip tooltip-right"
		data-tip={isVisited ? $t('adventures.visited') : $t('adventures.not_visited')}
	>
		{#if isVisited}
			<div class="badge badge-sm badge-success p-1 rounded-full shadow-sm">
				<Calendar class="w-4 h-4" />
			</div>
		{:else}
			<div class="badge badge-sm badge-warning p-1 rounded-full shadow-sm">
				<Clock class="w-4 h-4" />
			</div>
		{/if}
	</div>
</div>
