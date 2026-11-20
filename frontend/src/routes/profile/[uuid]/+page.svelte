<script lang="ts">
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { untrack } from 'svelte';
	import { t } from 'svelte-i18n';
	import CollectionCard from '#lib/components/cards/CollectionCard.svelte';
	import ProfileHero from '#lib/components/profile/ProfileHero.svelte';
	import ProfileLocations from '#lib/components/profile/ProfileLocations.svelte';
	import ProfileMap from '#lib/components/profile/ProfileMap.svelte';
	import ProfileEmbed from '#lib/components/profile/ProfileEmbed.svelte';
	import ProfileStats from '#lib/components/profile/ProfileStats.svelte';
	import ProfileActivity from '#lib/components/profile/ProfileActivity.svelte';
	import type { ProfileStatsData } from '#lib/components/profile/types.js';
	import type { Collection, User } from '#lib/types.js';

	import MapMarker from '~icons/mdi/map-marker-outline';
	import Suitcase from '~icons/mdi/bag-suitcase-outline';
	import MapIcon from '~icons/mdi/map-outline';
	import ChartBox from '~icons/mdi/chart-box-outline';
	import AlertCircle from '~icons/mdi/alert-circle-outline';
	import FolderOff from '~icons/mdi/folder-off-outline';

	let { data } = $props();

	// `data.user` is the signed-in viewer (from the layout); the page's own user is `profile`.
	const profile: User = $derived(data.profile);
	const viewer: User | null = $derived(data.user ?? null);
	const collections: Collection[] = $derived(data.collections);
	const isOwn = $derived(!!viewer && viewer.username === profile.username);
	const system = $derived(viewer?.measurement_system ?? 'metric');

	const TABS = ['locations', 'collections', 'map', 'stats'] as const;
	type Tab = (typeof TABS)[number];

	const requested = untrack(() => page.url.searchParams.get('tab'));
	let tab = $state<Tab>(TABS.includes(requested as Tab) ? (requested as Tab) : 'locations');
	// The map is heavy, so it is only built once someone opens it.
	let mapOpened = $state(requested === 'map');

	function selectTab(next: Tab) {
		tab = next;
		if (next === 'map') mapOpened = true;
		const url = new URL(page.url.href);
		if (next === 'locations') url.searchParams.delete('tab');
		else url.searchParams.set('tab', next);
		replaceState(url, page.state);
	}

	// A stats failure can be retried without reloading the page.
	let retriedStats = $state<ProfileStatsData | null>(null);
	let retrying = $state(false);
	async function retryStats() {
		retrying = true;
		try {
			const res = await fetch(`/api/users/${encodeURIComponent(profile.username)}/stats/`);
			if (res.ok) retriedStats = await res.json();
		} finally {
			retrying = false;
		}
	}

	const title = $derived(
		[profile.first_name, profile.last_name].filter(Boolean).join(' ') || profile.username
	);
</script>

<svelte:head>
	<title>{title} (@{profile.username}) | AdventureLog</title>
	<meta name="description" content={`${title}'s travels on AdventureLog`} />
</svelte:head>

<div class="min-h-screen bg-base-200/40">
	<ProfileHero {profile} {viewer} stats={data.stats} {isOwn} />

	<div class="mx-auto max-w-6xl px-4 pb-16 sm:px-6">
		<div
			role="tablist"
			class="tabs tabs-border sticky top-0 z-10 -mx-4 overflow-x-auto bg-base-200/80 px-4 backdrop-blur sm:mx-0 sm:px-0"
		>
			{#each [{ id: 'locations', icon: MapMarker, label: $t('profile.tab_locations') }, { id: 'collections', icon: Suitcase, label: $t('profile.tab_collections') }, { id: 'map', icon: MapIcon, label: $t('profile.tab_map') }, { id: 'stats', icon: ChartBox, label: $t('profile.tab_stats') }] as item (item.id)}
				<button
					role="tab"
					class="tab gap-2 whitespace-nowrap {tab === item.id ? 'tab-active font-semibold' : ''}"
					aria-selected={tab === item.id}
					onclick={() => selectTab(item.id as Tab)}
				>
					<item.icon class="h-4 w-4" />
					{item.label}
					{#if item.id === 'collections' && collections.length > 0}
						<span class="badge badge-sm badge-ghost">{collections.length}</span>
					{/if}
				</button>
			{/each}
		</div>

		<div class="pt-6">
			{#if tab === 'locations'}
				{#await data.locations}
					<div class="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
						{#each Array(6) as _}
							<div class="skeleton h-72 rounded-box"></div>
						{/each}
					</div>
				{:then initial}
					<ProfileLocations username={profile.username} {viewer} {isOwn} {initial} />
				{/await}
			{:else if tab === 'collections'}
				{#if collections.length === 0}
					<div
						class="flex flex-col items-center gap-3 rounded-box border border-base-300/60 bg-base-100 py-14 text-center"
					>
						<FolderOff class="h-10 w-10 text-base-content/30" />
						<p class="max-w-md text-base-content/60">
							{isOwn ? $t('profile.no_collections_own') : $t('profile.no_shared_collections')}
						</p>
					</div>
				{:else}
					<div class="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
						{#each collections as collection (collection.id)}
							<CollectionCard {collection} type="" user={viewer} />
						{/each}
					</div>
				{/if}
			{/if}

			{#if mapOpened}
				<div class:hidden={tab !== 'map'}>
					{#await data.pins}
						<div class="skeleton h-[60vh] min-h-[320px] rounded-box"></div>
					{:then pins}
						{#if pins}
							<ProfileMap {pins} basemap={viewer?.map_style} {isOwn} />
						{:else}
							<div
								class="flex flex-col items-center gap-3 rounded-box border border-base-300/60 bg-base-100 py-14 text-center"
							>
								<AlertCircle class="h-10 w-10 text-warning" />
								<p class="text-base-content/70">{$t('profile.section_failed')}</p>
							</div>
						{/if}
					{/await}
					{#if isOwn}
						<ProfileEmbed {profile} />
					{/if}
				</div>
			{/if}

			{#if tab === 'stats'}
				{#await data.stats}
					<div class="grid gap-4 md:grid-cols-3">
						{#each Array(3) as _}
							<div class="skeleton h-40 rounded-box"></div>
						{/each}
					</div>
				{:then loaded}
					{@const stats = retriedStats ?? loaded}
					{#if !stats}
						<div
							class="flex flex-col items-center gap-3 rounded-box border border-base-300/60 bg-base-100 py-14 text-center"
						>
							<AlertCircle class="h-10 w-10 text-warning" />
							<p class="text-base-content/70">{$t('profile.section_failed')}</p>
							<button class="btn btn-sm btn-primary" onclick={retryStats} disabled={retrying}>
								{#if retrying}<span class="loading loading-spinner loading-xs"></span>{/if}
								{$t('profile.retry')}
							</button>
						</div>
					{:else}
						<div class="space-y-8">
							<section>
								<h2 class="mb-3 text-lg font-semibold">{$t('profile.world_progress')}</h2>
								<ProfileStats {stats} />
							</section>
							{#if stats.activities_overall?.total_count > 0}
								<section>
									<h2 class="mb-3 text-lg font-semibold">{$t('adventures.activity_statistics')}</h2>
									<ProfileActivity {stats} {system} />
								</section>
							{/if}
						</div>
					{/if}
				{/await}
			{/if}
		</div>
	</div>
</div>
