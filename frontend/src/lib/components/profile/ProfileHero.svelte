<script lang="ts">
	import { t } from 'svelte-i18n';
	import UserAvatar from '#lib/components/UserAvatar.svelte';
	import { dateFormatFromUser, formatDisplayDate } from '#lib/dateFormat.js';
	import { addToast } from '#lib/toasts.js';
	import type { User } from '#lib/types.js';
	import { rankKey } from './format.js';
	import type { ProfileStatsData } from './types.js';

	import Calendar from '~icons/mdi/calendar-month-outline';
	import Award from '~icons/mdi/medal-outline';
	import ShareVariant from '~icons/mdi/share-variant-outline';
	import Pencil from '~icons/mdi/pencil-outline';
	import Lock from '~icons/mdi/lock-outline';
	import Earth from '~icons/mdi/earth';
	import MapMarker from '~icons/mdi/map-marker-outline';
	import Suitcase from '~icons/mdi/bag-suitcase-outline';
	import City from '~icons/mdi/city-variant-outline';

	interface Props {
		profile: User;
		viewer: User | null;
		/** Resolves to null when the stats could not be loaded. */
		stats: Promise<ProfileStatsData | null>;
		isOwn: boolean;
	}

	let { profile, viewer, stats, isOwn }: Props = $props();

	const dateFormat = $derived(dateFormatFromUser(viewer));
	const fullName = $derived(
		[profile.first_name, profile.last_name].filter(Boolean).join(' ') || profile.username
	);

	async function share() {
		const url = window.location.origin + window.location.pathname;
		try {
			if (navigator.share) {
				await navigator.share({ title: fullName, url });
				return;
			}
			await navigator.clipboard.writeText(url);
			addToast('success', $t('profile.link_copied'));
		} catch (err) {
			// A cancelled share sheet is not an error.
			if ((err as Error)?.name !== 'AbortError') addToast('error', $t('adventures.copy_failed'));
		}
	}
</script>

<section class="relative overflow-hidden border-b border-base-300/60 bg-base-100">
	<div
		class="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-secondary/10"
	></div>
	<div class="relative mx-auto max-w-6xl px-4 pb-6 pt-8 sm:px-6 sm:pt-12">
		<div class="flex flex-col items-center gap-5 text-center sm:flex-row sm:items-end sm:text-left">
			<!-- A fixed box: a photo ignores size classes on the image itself. -->
			<div
				class="h-24 w-24 shrink-0 overflow-hidden rounded-full shadow-lg ring-2 ring-primary/70 ring-offset-4 ring-offset-base-100 sm:h-28 sm:w-28"
			>
				<UserAvatar
					user={profile}
					alt={fullName}
					className="h-full w-full rounded-full"
					textClass="text-3xl"
				/>
			</div>

			<div class="min-w-0 flex-1 space-y-2">
				<div>
					<h1 class="truncate text-3xl font-bold tracking-tight sm:text-4xl">{fullName}</h1>
					<p class="text-base-content/60">@{profile.username}</p>
				</div>

				<div class="flex flex-wrap items-center justify-center gap-2 text-sm sm:justify-start">
					{#if profile.date_joined}
						<span class="badge badge-ghost gap-1.5 py-3">
							<Calendar class="h-4 w-4" />
							{$t('profile.member_since')}
							{formatDisplayDate(profile.date_joined, dateFormat, {
								timeZone: 'UTC',
								month: 'long'
							})}
						</span>
					{/if}
					{#await stats then s}
						{#if s && s.location_count > 0}
							<span class="badge badge-primary badge-soft gap-1.5 py-3">
								<Award class="h-4 w-4" />
								{$t(`profile.rank_${rankKey(s.location_count)}`)}
							</span>
						{/if}
					{/await}
					{#if isOwn}
						<span class="badge badge-ghost gap-1.5 py-3">
							{#if profile.profile_visibility === 'private'}
								<Lock class="h-4 w-4" />
								{$t('profile.only_you')}
							{:else if profile.profile_visibility === 'signed_in'}
								<Lock class="h-4 w-4" />
								{$t('profile.visible_signed_in')}
							{:else}
								<Earth class="h-4 w-4" />
								{$t('profile.visible_public')}
							{/if}
						</span>
					{/if}
				</div>
			</div>

			<div class="flex shrink-0 gap-2">
				<button class="btn btn-sm btn-ghost gap-2" onclick={share}>
					<ShareVariant class="h-4 w-4" />
					{$t('profile.share_profile')}
				</button>
				{#if isOwn}
					<a href="/settings" class="btn btn-sm btn-primary gap-2">
						<Pencil class="h-4 w-4" />
						{$t('profile.edit_profile')}
					</a>
				{/if}
			</div>
		</div>

		<!-- At-a-glance numbers; they arrive with the stats, so they show placeholders first. -->
		<div class="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
			{#await stats}
				{#each Array(4) as _}
					<div class="skeleton h-[72px] rounded-box"></div>
				{/each}
			{:then s}
				{#if s}
					{@const tiles = [
						{ icon: MapMarker, value: s.location_count, label: $t('locations.locations') },
						{ icon: Suitcase, value: s.trips_count, label: $t('navbar.collections') },
						{ icon: Earth, value: s.visited_country_count, label: $t('profile.visited_countries') },
						{ icon: City, value: s.visited_city_count, label: $t('profile.visited_cities') }
					]}
					{#each tiles as tile}
						<div
							class="flex items-center gap-3 rounded-box border border-base-300/60 bg-base-100/80 p-3 backdrop-blur"
						>
							<div class="rounded-lg bg-primary/10 p-2 text-primary">
								<tile.icon class="h-5 w-5" />
							</div>
							<div class="min-w-0">
								<div class="text-xl font-bold leading-tight">{tile.value.toLocaleString()}</div>
								<div class="truncate text-xs text-base-content/60">{tile.label}</div>
							</div>
						</div>
					{/each}
				{/if}
			{/await}
		</div>
	</div>
</section>
