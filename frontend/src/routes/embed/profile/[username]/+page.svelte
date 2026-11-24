<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { t } from 'svelte-i18n';
	import ProfileMap from '#lib/components/profile/ProfileMap.svelte';
	import UserAvatar from '#lib/components/UserAvatar.svelte';
	import { dateFormatFromUser, formatDisplayDate } from '#lib/dateFormat.js';
	import { rankKey } from '#lib/components/profile/format.js';

	import ChevronLeft from '~icons/mdi/chevron-left';
	import AccountIcon from '~icons/mdi/account-circle-outline';
	import Calendar from '~icons/mdi/calendar-month-outline';
	import Medal from '~icons/mdi/medal-outline';

	let { data } = $props();

	const name = $derived(
		[data.profile.first_name, data.profile.last_name].filter(Boolean).join(' ') ||
			data.profile.username
	);
	const profileUrl = $derived(`/profile/${encodeURIComponent(data.profile.username)}`);
	const stats = $derived(data.stats);

	// The panel starts folded when the embed asks for it (`?profile=hide`) and in small frames,
	// so the map is what you see. It can always be opened.
	let open = $state(untrack(() => !data.collapsed));
	onMount(() => {
		if (window.innerWidth < 640) open = false;
	});

	const tiles = $derived(
		stats
			? [
					{ value: stats.location_count, label: $t('locations.locations') },
					{ value: stats.trips_count, label: $t('navbar.collections') },
					{ value: stats.visited_country_count, label: $t('profile.visited_countries') },
					{ value: stats.visited_city_count, label: $t('profile.visited_cities') }
				]
			: []
	);
</script>

<svelte:head>
	<title>{name} | AdventureLog</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="relative h-[100dvh] w-full overflow-hidden bg-base-100">
	{#if data.pins.length > 0}
		<ProfileMap pins={data.pins} embedded />
	{:else}
		<div class="grid h-full place-items-center p-6 text-center text-base-content/60">
			{$t('profile.map_empty')}
		</div>
	{/if}

	<!-- The profile panel floats over the map, so opening and closing it never resizes the map. -->
	{#if open}
		<aside
			class="absolute left-3 top-3 z-20 flex max-h-[calc(100%-4.5rem)] w-[min(18rem,calc(100%-1.5rem))] flex-col gap-4 overflow-y-auto rounded-box border border-base-300 bg-base-100/95 p-4 shadow-xl backdrop-blur"
		>
			<button
				class="btn btn-circle btn-ghost btn-xs absolute right-2 top-2"
				aria-label={$t('profile.embed_hide_profile')}
				onclick={() => (open = false)}
			>
				<ChevronLeft class="h-4 w-4" />
			</button>

			<div class="flex items-center gap-3 pr-6">
				<!-- A fixed box: a photo ignores size classes on the image and would fill the row. -->
				<div
					class="h-16 w-16 shrink-0 overflow-hidden rounded-full ring-2 ring-primary/40 ring-offset-2 ring-offset-base-100"
				>
					<UserAvatar
						user={data.profile}
						alt={name}
						className="h-full w-full rounded-full"
						textClass="text-xl"
					/>
				</div>
				<div class="min-w-0">
					<h1 class="break-words text-xl font-bold leading-tight tracking-tight">{name}</h1>
					<div class="mt-0.5 truncate text-sm font-medium text-primary">
						@{data.profile.username}
					</div>
				</div>
			</div>

			<div class="flex flex-col gap-1.5 text-xs text-base-content/70">
				{#if data.profile.date_joined}
					<span class="flex items-center gap-1.5">
						<Calendar class="h-4 w-4" />
						{$t('profile.member_since')}
						{formatDisplayDate(data.profile.date_joined, dateFormatFromUser(null), {
							timeZone: 'UTC',
							month: 'long'
						})}
					</span>
				{/if}
				{#if stats && stats.location_count > 0}
					<span class="flex items-center gap-1.5">
						<Medal class="h-4 w-4" />
						{$t(`profile.rank_${rankKey(stats.location_count)}`)}
					</span>
				{/if}
			</div>

			{#if tiles.length}
				<div class="grid grid-cols-2 gap-2">
					{#each tiles as tile}
						<div class="rounded-lg border border-base-300/70 bg-base-200/50 px-3 py-2">
							<div class="text-lg font-bold leading-tight">{tile.value.toLocaleString()}</div>
							<div class="truncate text-[11px] text-base-content/60">{tile.label}</div>
						</div>
					{/each}
				</div>
			{/if}

			<a href={profileUrl} target="_blank" rel="noopener" class="btn btn-sm btn-primary">
				{$t('profile.view_full_profile', { values: { name } })}
			</a>
		</aside>
	{:else}
		<button
			class="btn btn-sm absolute left-3 top-3 z-20 gap-2 border-base-300 bg-base-100 shadow-md"
			aria-label={$t('profile.embed_show_profile')}
			onclick={() => (open = true)}
		>
			<AccountIcon class="h-4 w-4" />
			<span class="max-w-[10rem] truncate">{name}</span>
		</button>
	{/if}

	<!-- Bottom-left: the map's own attribution sits bottom-right. -->
	<div
		class="pointer-events-none absolute bottom-3 left-3 z-10 flex max-w-[calc(100%-7rem)] items-center gap-2"
	>
		<a
			href="https://adventurelog.app"
			target="_blank"
			rel="noopener"
			class="group pointer-events-auto inline-flex h-8 shrink-0 items-center gap-2 rounded-full border border-base-300 bg-base-100 py-1 pl-1.5 pr-3 text-xs text-base-content/70 shadow-md transition hover:border-primary/40 hover:text-base-content"
		>
			<img src="/adventurelog.svg" alt="" class="h-5 w-5 rounded-md" />
			<span>
				{$t('profile.powered_by_prefix')}
				<strong class="font-semibold text-base-content group-hover:text-primary"
					>AdventureLog</strong
				>
			</span>
		</a>
	</div>
</div>
