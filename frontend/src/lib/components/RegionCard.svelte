<script lang="ts">
	import { goto } from '$app/navigation';
	import { addToast } from '$lib/toasts';
	import type { Region, VisitedRegion } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { t } from 'svelte-i18n';

	export let region: Region;
	export let visited: boolean | undefined;

	function goToCity() {
		console.log(region);
		goto(`/worldtravel/${region.id.split('-')[0]}/${region.id}`);
	}

	async function markVisited() {
		let res = await fetch(`/api/visitedregion/`, {
			headers: { 'Content-Type': 'application/json' },
			method: 'POST',
			body: JSON.stringify({ region: region.id })
		});
		if (res.ok) {
			visited = true;
			let data = await res.json();
			addToast(
				'success',
				`${$t('worldtravel.visit_to')} ${region.name} ${$t('worldtravel.marked_visited')}`
			);
			dispatch('visit', data);
		} else {
			console.error($t('worldtravel.region_failed_visited'));
			addToast('error', `${$t('worldtravel.failed_to_mark_visit')} ${region.name}`);
		}
	}
	async function removeVisit() {
		let res = await fetch(`/api/visitedregion/${region.id}`, {
			headers: { 'Content-Type': 'application/json' },
			method: 'DELETE'
		});
		if (res.ok) {
			visited = false;
			addToast('info', `${$t('worldtravel.visit_to')} ${region.name} ${$t('worldtravel.removed')}`);
			dispatch('remove', region);
		} else {
			console.error($t('worldtravel.visit_remove_failed'));
			addToast('error', `${$t('worldtravel.failed_to_remove_visit')} ${region.name}`);
		}
	}
</script>

<div
	class="card w-full max-w-md bg-base-300 text-base-content shadow-2xl hover:shadow-3xl transition-all duration-300 border border-base-300 hover:border-primary/20 group overflow-hidden"
>
	<div class="card-body p-6 space-y-4">
		<!-- Header -->
		<a
			href="/worldtravel/{region.id.split('-')[0]}/{region.id}"
			class="text-xl font-bold text-left hover:text-primary transition-colors duration-200 line-clamp-2 group-hover:underline block"
		>
			{region.name}
		</a>

		<!-- Metadata Badges -->
		<div class="flex flex-wrap gap-2">
			<div class="badge badge-primary">{region.country_name}</div>
			<div class="badge badge-neutral">
				{region.num_cities}
				{$t('worldtravel.cities')}
			</div>
			<div class="badge badge-neutral-300">ID: {region.id}</div>
		</div>

		<!-- Actions -->
		<div class="pt-4 border-t border-base-300 flex flex-wrap gap-2 justify-end">
			{#if visited === false}
				<button class="btn btn-primary btn-sm" on:click={markVisited}>
					{$t('adventures.mark_visited')}
				</button>
			{/if}
			{#if visited === true}
				<button class="btn btn-warning btn-sm" on:click={removeVisit}>
					{$t('adventures.remove')}
				</button>
			{/if}
			{#if region.num_cities > 0}
				<button class="btn btn-neutral btn-sm" on:click={goToCity}>
					{$t('worldtravel.view_cities')}
				</button>
			{/if}
		</div>
	</div>
</div>

<style>
	.truncate {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
</style>
