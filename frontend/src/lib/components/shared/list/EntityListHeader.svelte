<script lang="ts">
	/**
	 * EntityListHeader - Shared header for entity list pages
	 * Displays title, subtitle, and quick stats
	 */
	import { t } from 'svelte-i18n';
	import Filter from '~icons/mdi/filter-variant';
	import Eye from '~icons/mdi/eye';
	import Calendar from '~icons/mdi/calendar';

	export let title: string;
	export let subtitle: string;
	export let icon: any; // Svelte component
	export let count: number = 0;
	export let visitedCount: number = 0;
	export let plannedCount: number = 0;
	export let showVisitedPlanned: boolean = true;
	export let onToggleSidebar: () => void = () => {};
</script>

<div class="sticky top-0 z-30 bg-base-100/80 backdrop-blur-lg border-b border-base-300">
	<div class="container mx-auto px-6 py-4">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-4">
				<button class="btn btn-ghost btn-square lg:hidden" on:click={onToggleSidebar}>
					<Filter class="w-5 h-5" />
				</button>
				<div class="flex items-center gap-3">
					<div class="p-2 bg-primary/10 rounded-xl">
						<svelte:component this={icon} class="w-8 h-8 text-primary" />
					</div>
					<div>
						<h1 class="text-3xl font-bold bg-clip-text text-primary">
							{title}
						</h1>
						<p class="text-sm text-base-content/60">
							{subtitle}
						</p>
					</div>
				</div>
			</div>

			<!-- Quick Stats -->
			{#if showVisitedPlanned}
				<div class="hidden md:flex items-center gap-3">
					<div class="stats stats-horizontal bg-base-200/50 border border-base-300/50">
						<div class="stat py-2 px-4">
							<div class="stat-figure text-primary">
								<svelte:component this={icon} class="w-5 h-5" />
							</div>
							<div class="stat-title text-xs">{$t('adventures.total') || 'Total'}</div>
							<div class="stat-value text-lg">{count}</div>
						</div>
						<div class="stat py-2 px-4">
							<div class="stat-figure text-success">
								<Eye class="w-5 h-5" />
							</div>
							<div class="stat-title text-xs">{$t('adventures.visited')}</div>
							<div class="stat-value text-lg text-success">{visitedCount}</div>
						</div>
						<div class="stat py-2 px-4">
							<div class="stat-figure text-warning">
								<Calendar class="w-5 h-5" />
							</div>
							<div class="stat-title text-xs">{$t('adventures.planned')}</div>
							<div class="stat-value text-lg text-warning">{plannedCount}</div>
						</div>
					</div>
				</div>
			{/if}
		</div>
	</div>
</div>
