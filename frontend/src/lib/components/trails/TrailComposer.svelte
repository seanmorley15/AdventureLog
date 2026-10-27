<script lang="ts">
	import { apiErrorMessage } from '#lib/api/index.js';
	import { onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import type { Trail, WandererTrail } from '#lib/types.js';
	import { addToast } from '#lib/toasts.js';
	import WandererCard from '#lib/components/cards/WandererCard.svelte';
	import PlusIcon from '~icons/mdi/plus';
	import LinkIcon from '~icons/mdi/link';

	interface DayChoice {
		index: number;
		label: string;
	}

	interface Props {
		/** Place trail. */
		locationId?: string | null;
		/** Day trail. Exactly one of locationId or dayId. */
		dayId?: string | null;
		userIsOwner?: boolean;
		/** Show the link form, the Wanderer picker, or both. */
		mode?: 'link' | 'wanderer' | 'both';
		dayChoices?: DayChoice[];
		onCreated: (trail: Trail) => void;
		onCancel?: () => void;
	}

	let {
		locationId = null,
		dayId = null,
		userIsOwner = false,
		mode = 'both',
		dayChoices = [],
		onCreated,
		onCancel
	}: Props = $props();

	let trailName = $state('');
	let trailLink = $state('');
	let trailWandererId = $state('');
	let trailWandererAuthorUsername = $state('');
	let trailWandererAuthorDomain = $state('');
	let spanEnd = $state('');
	let trailError = $state('');
	let isTrailLoading = $state(false);
	let isWandererEnabled = $state(false);
	let searchQuery = $state('');
	let isSearching = $state(false);
	let wandererFetchedTrails: WandererTrail[] = $state([]);
	let linkOpen = $state(true);
	let wandererOpen = $state(true);
	const showLink = $derived(mode === 'both' ? linkOpen : mode === 'link');
	const showWanderer = $derived(mode === 'both' ? wandererOpen : mode === 'wanderer');

	function wandererAuthorFromTrail(trail: WandererTrail) {
		const author = trail.expand?.author;
		return {
			username: (author?.preferred_username || author?.username || '').trim(),
			domain: (author?.domain || '').trim().replace(/^@+/, '')
		};
	}

	async function createTrail() {
		isTrailLoading = true;
		trailError = '';
		if (trailWandererId.trim()) {
			trailLink = '';
		} else if (!trailLink.trim()) {
			trailError = $t('adventures.trail_link_required');
			isTrailLoading = false;
			return;
		}
		if (!trailName.trim()) {
			trailError = $t('adventures.trail_name');
			isTrailLoading = false;
			return;
		}

		const trailData: Record<string, unknown> = {
			name: trailName.trim(),
			link: trailLink.trim() || null,
			wanderer_id: trailWandererId.trim() || null,
			wanderer_author_username: trailWandererAuthorUsername.trim() || null,
			wanderer_author_domain: trailWandererAuthorDomain.trim() || null
		};
		if (locationId) trailData.location = locationId;
		if (dayId) {
			trailData.day = dayId;
			if (spanEnd) trailData.span_end_index = Number(spanEnd);
		}

		try {
			const res = await fetch('/api/trails/', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(trailData)
			});
			if (!res.ok) {
				const errorData = await res.json().catch(() => ({}));
				throw new Error(apiErrorMessage(errorData, 'Failed to create trail'));
			}
			const newTrail = (await res.json()) as Trail;
			addToast('success', $t('adventures.trail_created_successfully'));
			onCreated(newTrail);
		} catch (error) {
			trailError = error instanceof Error ? error.message : 'Failed to create trail';
			addToast('error', $t('adventures.trail_creation_failed'));
		} finally {
			isTrailLoading = false;
		}
	}

	async function fetchWandererTrails(filter = '') {
		isSearching = true;
		try {
			const url = new URL('/api/integrations/wanderer/trails', window.location.origin);
			url.searchParams.set('expand', 'author');
			if (filter) url.searchParams.set('filter', filter);
			const res = await fetch(url);
			if (res.ok) {
				const itemsResponse = await res.json();
				wandererFetchedTrails = itemsResponse.items || [];
			} else {
				wandererFetchedTrails = [];
			}
		} catch (error) {
			console.error('Wanderer search failed:', error);
			wandererFetchedTrails = [];
		} finally {
			isSearching = false;
		}
	}

	let searchTimeout: ReturnType<typeof setTimeout> | undefined;
	function debouncedSearch() {
		clearTimeout(searchTimeout);
		searchTimeout = setTimeout(() => {
			const filter = searchQuery.trim() ? `name~"${searchQuery}"` : '';
			void fetchWandererTrails(filter);
		}, 300);
	}

	async function linkWandererTrail(event: CustomEvent<WandererTrail>) {
		const trail = event.detail;
		const { username, domain } = wandererAuthorFromTrail(trail);
		trailName = trail.name;
		trailLink = '';
		trailWandererId = trail.id;
		trailWandererAuthorUsername = username;
		trailWandererAuthorDomain = domain;
		await createTrail();
	}

	onMount(async () => {
		if (!userIsOwner) return;
		try {
			const res = await fetch('/api/integrations');
			if (!res.ok) return;
			const data = await res.json();
			isWandererEnabled = Boolean(data.wanderer?.exists);
			if (isWandererEnabled && showWanderer) await fetchWandererTrails();
		} catch (error) {
			console.error('Error checking integrations:', error);
		}
	});
</script>

<div class="space-y-6">
	{#if mode === 'both'}
		<div class="flex flex-wrap gap-2">
			<button
				type="button"
				class="btn btn-sm gap-2 {showLink ? 'btn-accent' : 'btn-outline'}"
				onclick={() => (linkOpen = !linkOpen)}
			>
				<LinkIcon class="h-4 w-4" />
				{$t('adventures.add_trail')}
			</button>
			{#if userIsOwner}
				<button
					type="button"
					class="btn btn-sm gap-2 {showWanderer ? 'btn-accent' : 'btn-outline'}"
					onclick={() => {
						wandererOpen = !wandererOpen;
						if (wandererOpen && isWandererEnabled && wandererFetchedTrails.length === 0) {
							void fetchWandererTrails();
						}
					}}
				>
					<PlusIcon class="h-4 w-4" />
					{$t('adventures.add_wanderer_trail')}
				</button>
			{/if}
		</div>
	{/if}

	{#if showLink}
		<div class="rounded-lg border border-accent/20 bg-accent/5 p-4">
			<h4 class="mb-1 font-medium text-accent">{$t('adventures.add_new_trail')}</h4>
			<p class="mb-3 text-sm text-base-content/60">{$t('itinerary.trail_link_hint')}</p>
			<div class="grid gap-3">
				<label class="flex flex-col">
					<span class="field-label">{$t('adventures.trail_name')}</span>
					<input type="text" class="input" bind:value={trailName} disabled={isTrailLoading} />
				</label>
				<label class="flex flex-col">
					<span class="field-label">{$t('adventures.external_link')}</span>
					<input
						type="url"
						class="input"
						placeholder="AllTrails, Trailforks, …"
						bind:value={trailLink}
						disabled={isTrailLoading || Boolean(trailWandererId)}
					/>
				</label>
				{#if dayId && dayChoices.length > 0}
					<label class="flex flex-col">
						<span class="field-label">{$t('itinerary.ends_on')}</span>
						<select class="select" bind:value={spanEnd}>
							<option value="">{$t('itinerary.same_day')}</option>
							{#each dayChoices as choice (choice.index)}
								<option value={String(choice.index)}>{choice.label}</option>
							{/each}
						</select>
					</label>
				{/if}
				{#if trailError}
					<div class="alert alert-error py-2">
						<span class="text-sm">{trailError}</span>
					</div>
				{/if}
				<div class="flex justify-end gap-2">
					{#if onCancel}
						<button
							type="button"
							class="btn btn-ghost btn-sm"
							disabled={isTrailLoading}
							onclick={onCancel}
						>
							{$t('adventures.cancel')}
						</button>
					{/if}
					<button
						type="button"
						class="btn btn-accent btn-sm"
						class:loading={isTrailLoading}
						disabled={isTrailLoading ||
							!trailName.trim() ||
							(!trailLink.trim() && !trailWandererId)}
						onclick={createTrail}
					>
						{$t('adventures.create_trail')}
					</button>
				</div>
			</div>
		</div>
	{/if}

	{#if showWanderer && userIsOwner}
		<div class="rounded-lg border border-accent/20 bg-accent/5 p-4">
			<h4 class="mb-3 font-medium text-accent">{$t('adventures.add_wanderer_trail')}</h4>
			{#if isWandererEnabled}
				<p class="mb-2 text-sm text-base-content/60">{$t('adventures.select_wanderer_trail')}:</p>
				<div class="relative mb-3">
					<input
						type="text"
						placeholder={$t('adventures.search_trails_placeholder') + '...'}
						class="input w-full pr-20"
						bind:value={searchQuery}
						oninput={debouncedSearch}
						onkeydown={(event) =>
							event.key === 'Enter' &&
							fetchWandererTrails(searchQuery.trim() ? `name~"${searchQuery}"` : '')}
					/>
					<div class="absolute right-2 top-1/2 flex -translate-y-1/2 gap-1">
						{#if searchQuery}
							<button
								type="button"
								class="btn btn-ghost btn-xs btn-circle"
								onclick={() => {
									searchQuery = '';
									void fetchWandererTrails();
								}}
							>
								✕
							</button>
						{/if}
					</div>
				</div>
				<div class="max-h-96 overflow-y-auto">
					{#if isSearching}
						<div class="flex justify-center py-8">
							<span class="loading loading-spinner loading-md"></span>
						</div>
					{:else if wandererFetchedTrails.length === 0}
						<div class="py-8 text-center text-base-content/60">
							{$t('adventures.no_trails_available')}
						</div>
					{:else}
						<div class="space-y-3">
							{#each wandererFetchedTrails as trail (trail.id)}
								<WandererCard {trail} on:link={linkWandererTrail} />
							{/each}
						</div>
					{/if}
				</div>
			{:else}
				<p class="text-sm text-base-content/60">{$t('adventures.wanderer_integration_error')}</p>
			{/if}
		</div>
	{/if}
</div>
