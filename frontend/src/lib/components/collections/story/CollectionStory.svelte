<script lang="ts">
	import { onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	import type { Collection, ContentImage } from '$lib/types';
	import {
		buildStory,
		readingPosition,
		type StoryChapter,
		type StoryPin
	} from '$lib/collections/story';
	import { formatDisplayDate, type DateFormatPreference } from '$lib/dateFormat';
	import { copyToClipboard } from '$lib/index';
	import { addToast } from '$lib/toasts';
	import ImageDisplayModal from '$lib/components/ImageDisplayModal.svelte';
	import UserAvatar from '$lib/components/UserAvatar.svelte';
	import StoryEntryCard from './StoryEntryCard.svelte';
	import StoryMap from './StoryMap.svelte';
	import ShareVariant from '~icons/mdi/share-variant';
	import ContentCopy from '~icons/mdi/content-copy';
	import MapIcon from '~icons/mdi/map-outline';
	import CalendarRange from '~icons/mdi/calendar-range';
	import MapMarkerMultiple from '~icons/mdi/map-marker-multiple-outline';
	import ImageMultiple from '~icons/mdi/image-multiple-outline';
	import Hiking from '~icons/mdi/hiking';

	interface Props {
		collection: Collection;
		dateFormat: DateFormatPreference;
		/** The link readers can share. Null hides the share actions. */
		shareUrl?: string | null;
		/** Inside the collection workspace: a shorter cover. The parent sets the height. */
		embedded?: boolean;
	}

	let { collection, dateFormat, shareUrl = null, embedded = false }: Props = $props();

	let story = $derived(buildStory(collection));
	let cover = $derived(collection.primary_image ?? story.photos[0] ?? null);
	let owner = $derived(
		(collection.collaborators ?? []).find((person) => person.is_owner && person.public_profile) ??
			null
	);
	let navChapters = $derived(story.chapters.filter((chapter) => chapter.index !== null));
	let hasMap = $derived(story.pins.length > 0 || story.tracks.length > 0);

	// Which day and stop the reader is on, from the scroll position. They drive the map.
	let activeChapter = $state<string | null>(null);
	let scrollEntry = $state<string | null>(null);
	// The card under the pointer: highlighted on the map without moving it.
	let hoverEntry = $state<string | null>(null);
	let mobileMapOpen = $state(true);
	let isWide = $state(false);
	// Maps need the browser; they mount after hydration.
	let mounted = $state(false);
	let lightbox = $state<{ images: ContentImage[]; index: number; name: string } | null>(null);
	let canNativeShare = $state(false);

	let pinLabels = $derived(new Map(story.pins.map((pin) => [pin.key, pin.label])));
	let pinnedKeys = $derived(new Set(story.pins.map((pin) => pin.key)));
	// Fly to the stop being read only while it belongs to the day being read.
	// The stop the map centers on. Always a pinned stop of the day being read.
	let focusKey = $derived(scrollEntry);
	let activeChapterData = $derived(
		story.chapters.find((chapter) => chapter.key === activeChapter) ?? null
	);

	function markdown(text: string | null | undefined) {
		return text ? DOMPurify.sanitize(marked(text) as string) : '';
	}

	function chapterTitle(chapter: StoryChapter) {
		if (chapter.key === 'trip') return $t('story.before_you_go');
		if (chapter.key === 'places') return $t('story.places');
		return $t('story.day_n', { values: { n: chapter.index } });
	}

	function dateRange() {
		if (collection.start_date && collection.end_date) {
			const start = formatDisplayDate(collection.start_date, dateFormat);
			const end = formatDisplayDate(collection.end_date, dateFormat);
			return start === end ? start : `${start} – ${end}`;
		}
		return story.dayCount ? $t('story.days_count', { values: { count: story.dayCount } }) : '';
	}

	function longDate(value: string | null) {
		if (!value) return '';
		try {
			return new Intl.DateTimeFormat(undefined, {
				weekday: 'long',
				month: 'long',
				day: 'numeric',
				year: 'numeric'
			}).format(new Date(`${value.slice(0, 10)}T12:00:00`));
		} catch {
			return formatDisplayDate(value, dateFormat);
		}
	}

	function scrollToId(id: string) {
		document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
	}

	function selectPin(pin: StoryPin) {
		hoverEntry = pin.key;
		activeChapter = pin.chapter;
		document
			.getElementById(`story-${pin.key}`)
			?.scrollIntoView({ behavior: 'smooth', block: 'center' });
	}

	async function copyShareLink() {
		if (!shareUrl) return;
		try {
			await copyToClipboard(shareUrl);
			addToast('success', $t('adventures.link_copied'));
		} catch {
			addToast('error', $t('adventures.copy_failed'));
		}
	}

	async function nativeShare() {
		if (!shareUrl) return;
		try {
			await navigator.share({ title: collection.name, url: shareUrl });
		} catch {
			// Cancelled by the reader.
		}
	}

	// Follow the reader inside the story's own scroll area. One reading line, 40% down
	// the column, decides both the day and the stop, so they can never disagree:
	// - the day is the last chapter whose top has passed the line;
	// - the stop is the last pinned card of that day that has passed the line, or the
	//   day's first pinned card when only its heading has. Entering a day therefore
	//   centers the map on that day's first place.
	// The cover, intro, and footer are chapters with no key: the map shows the whole trip.
	const READING_LINE = 0.4;
	const watchScroll = (node: HTMLElement) => {
		void story.chapters;
		let frame = 0;
		const update = () => {
			frame = 0;
			const line = node.getBoundingClientRect().top + node.clientHeight * READING_LINE;
			const sections = [...node.querySelectorAll<HTMLElement>('[data-chapter]')].map((el) => ({
				key: el.dataset.chapter || null,
				top: el.getBoundingClientRect().top,
				entries: [...el.querySelectorAll<HTMLElement>('[data-entry]')].map((entry) => ({
					key: entry.dataset.entry ?? '',
					top: entry.getBoundingClientRect().top
				}))
			}));
			const position = readingPosition(sections, line, pinnedKeys);
			activeChapter = position.chapter;
			scrollEntry = position.entry;
		};
		const onScroll = () => {
			if (!frame) frame = requestAnimationFrame(update);
		};
		node.addEventListener('scroll', onScroll, { passive: true });
		update();
		return () => {
			node.removeEventListener('scroll', onScroll);
			cancelAnimationFrame(frame);
		};
	};

	onMount(() => {
		canNativeShare = typeof navigator !== 'undefined' && typeof navigator.share === 'function';
		const query = window.matchMedia('(min-width: 1024px)');
		isWide = query.matches;
		mounted = true;
		const update = (event: MediaQueryListEvent) => (isWide = event.matches);
		query.addEventListener('change', update);
		return () => query.removeEventListener('change', update);
	});
</script>

{#if lightbox}
	<ImageDisplayModal
		images={lightbox.images}
		initialIndex={lightbox.index}
		name={lightbox.name}
		on:close={() => (lightbox = null)}
	/>
{/if}

{#snippet map(mapClass: string)}
	<StoryMap
		pins={story.pins}
		tracks={story.tracks}
		{activeChapter}
		{focusKey}
		highlightKey={hoverEntry}
		onPinClick={selectPin}
		{mapClass}
	/>
	<span
		class="pointer-events-none absolute left-3 top-3 z-10 flex items-center gap-1.5 rounded-full bg-base-100/90 px-3 py-1 text-xs font-semibold shadow"
	>
		<span
			class="h-2.5 w-2.5 rounded-full"
			style="background-color: {activeChapterData?.color ?? '#64748b'}"
		></span>
		{activeChapterData ? chapterTitle(activeChapterData) : $t('story.whole_trip')}
		{#if activeChapterData?.name}
			<span class="font-normal text-base-content/70">· {activeChapterData.name}</span>
		{/if}
	</span>
{/snippet}

<!-- The story scrolls in its own column, so the map beside it (or above it on a phone)
     always stays on screen. The parent gives this a height. -->
<article class="story flex h-full min-h-0 flex-col bg-base-100 lg:flex-row">
	{#if mounted && !isWide && hasMap}
		<div class="relative shrink-0 border-b border-base-300 {mobileMapOpen ? 'h-[34dvh]' : 'h-10'}">
			{#if mobileMapOpen}
				{@render map('h-full w-full')}
			{/if}
			<button
				type="button"
				class="btn btn-xs absolute bottom-2 right-2 z-10 gap-1 shadow"
				onclick={() => (mobileMapOpen = !mobileMapOpen)}
			>
				<MapIcon class="h-3.5 w-3.5" />
				{mobileMapOpen ? $t('story.hide_map') : $t('story.show_map')}
			</button>
		</div>
	{/if}

	<div
		class="min-h-0 flex-1 overflow-y-auto overscroll-contain {mounted && isWide && hasMap
			? 'lg:w-[56%] lg:max-w-[54rem] lg:flex-none'
			: ''}"
		{@attach watchScroll}
	>
		<!-- Cover. Reaching it again zooms the map back out to the whole trip. -->
		<header
			data-chapter=""
			class="relative flex items-end overflow-hidden bg-neutral text-neutral-content {embedded
				? 'min-h-[16rem] sm:min-h-[20rem]'
				: 'min-h-[55dvh]'}"
		>
			{#if cover}
				<img src={cover.image} alt="" class="absolute inset-0 h-full w-full object-cover" />
			{/if}
			<div class="absolute inset-0 bg-gradient-to-t from-black/85 via-black/35 to-black/10"></div>
			<div class="relative w-full px-5 pb-8 pt-20 text-white sm:px-8 sm:pb-10">
				<p class="text-xs font-semibold uppercase tracking-[0.2em] text-white/80 sm:text-sm">
					{collection.type === 'trip' ? $t('story.travel_story') : $t('story.collection_story')}
				</p>
				<h1 class="mt-2 text-4xl font-extrabold leading-tight sm:text-5xl">{collection.name}</h1>
				<div class="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-white/90">
					{#if owner}
						<a href={`/profile/${owner.username}`} class="flex items-center gap-2 hover:underline">
							<UserAvatar
								user={owner}
								alt={owner.username}
								className="h-8 w-8 rounded-full ring-2 ring-white/70"
								textClass="text-xs"
							/>
							<span>
								{$t('story.by', {
									values: {
										name:
											[owner.first_name, owner.last_name].filter(Boolean).join(' ') ||
											owner.username
									}
								})}
							</span>
						</a>
					{/if}
					{#if dateRange()}
						<span class="flex items-center gap-1.5"
							><CalendarRange class="h-4 w-4" />{dateRange()}</span
						>
					{/if}
					{#if story.placeCount}
						<span class="flex items-center gap-1.5">
							<MapMarkerMultiple class="h-4 w-4" />
							{$t('story.places_count', { values: { count: story.placeCount } })}
						</span>
					{/if}
					{#if story.photos.length}
						<span class="flex items-center gap-1.5">
							<ImageMultiple class="h-4 w-4" />
							{$t('story.photos_count', { values: { count: story.photos.length } })}
						</span>
					{/if}
					{#if story.distanceMeters > 0}
						<span class="flex items-center gap-1.5">
							<Hiking class="h-4 w-4" />
							{(story.distanceMeters / 1000).toFixed(1)} km
						</span>
					{/if}
				</div>
				{#if shareUrl}
					<div class="mt-6 flex flex-wrap gap-2">
						{#if canNativeShare}
							<button type="button" class="btn btn-sm gap-1" onclick={nativeShare}>
								<ShareVariant class="h-4 w-4" />
								{$t('story.share')}
							</button>
						{/if}
						<button
							type="button"
							class="btn btn-sm btn-ghost gap-1 bg-white/15 text-white hover:bg-white/25"
							onclick={copyShareLink}
						>
							<ContentCopy class="h-4 w-4" />
							{$t('share.copy_link')}
						</button>
					</div>
				{/if}
			</div>
		</header>

		{#if collection.description}
			<section data-chapter="" class="px-5 py-8 sm:px-8">
				<div class="prose max-w-none sm:prose-lg first-letter:text-5xl first-letter:font-bold">
					{@html markdown(collection.description)}
				</div>
			</section>
		{/if}

		<!-- Day navigator -->
		{#if navChapters.length > 1}
			<nav
				class="sticky top-0 z-20 border-y border-base-300 bg-base-100/90 backdrop-blur"
				aria-label={$t('story.days')}
			>
				<div class="flex gap-2 overflow-x-auto px-5 py-2 sm:px-8">
					{#each navChapters as chapter (chapter.key)}
						<button
							type="button"
							class="btn btn-sm shrink-0 rounded-full {activeChapter === chapter.key
								? 'text-white'
								: 'btn-ghost'}"
							style={activeChapter === chapter.key ? `background-color: ${chapter.color}` : ''}
							onclick={() => scrollToId(`chapter-${chapter.key}`)}
						>
							{chapterTitle(chapter)}
						</button>
					{/each}
				</div>
			</nav>
		{/if}

		<div class="space-y-14 px-5 py-8 sm:px-8">
			{#if story.chapters.length === 0}
				<p class="py-16 text-center text-base-content/60">{$t('story.empty')}</p>
			{/if}
			{#each story.chapters as chapter (chapter.key)}
				<section id={`chapter-${chapter.key}`} data-chapter={chapter.key} class="scroll-mt-16">
					<header class="mb-6">
						<p class="text-sm font-bold uppercase tracking-widest" style="color: {chapter.color}">
							{chapterTitle(chapter)}
							{#if chapter.date}
								<span class="font-medium normal-case tracking-normal text-base-content/60">
									· {longDate(chapter.date)}
								</span>
							{/if}
						</p>
						{#if chapter.name}
							<h2 class="mt-1 text-3xl font-bold leading-tight">{chapter.name}</h2>
						{/if}
						{#if chapter.description}
							<div class="prose mt-3 max-w-none text-base-content/80">
								{@html markdown(chapter.description)}
							</div>
						{/if}
					</header>

					{#if !chapter.entries.length && !chapter.photos.length}
						<p class="italic text-base-content/60">{$t('story.free_day')}</p>
					{/if}
					{#if chapter.entries.length}
						<ol
							class="relative space-y-6 border-l-2 pl-6 sm:pl-8"
							style="border-color: {chapter.color}33"
						>
							{#each chapter.entries as entry (entry.key)}
								<li
									class="relative"
									data-entry={entry.key}
									onmouseenter={() => (hoverEntry = entry.key)}
									onmouseleave={() => (hoverEntry = null)}
									onfocusin={() => (hoverEntry = entry.key)}
								>
									<span
										class="absolute -left-[1.95rem] top-6 h-3.5 w-3.5 rounded-full border-2 border-base-100 sm:-left-[2.45rem]"
										style="background-color: {chapter.color}"
										aria-hidden="true"
									></span>
									<StoryEntryCard
										{entry}
										{dateFormat}
										color={chapter.color}
										pinLabel={pinLabels.get(entry.key) ?? null}
										active={focusKey === entry.key || hoverEntry === entry.key}
										onPhotos={(images, index, name) => (lightbox = { images, index, name })}
									/>
								</li>
							{/each}
						</ol>
					{/if}

					{#if chapter.photos.length}
						<div class="mt-6 grid grid-cols-2 gap-2 sm:grid-cols-3">
							{#each chapter.photos as photo, i (photo.id ?? photo.image)}
								<button
									type="button"
									class="aspect-square overflow-hidden rounded-xl bg-base-200 {i === 0 &&
									chapter.photos.length > 2
										? 'col-span-2 row-span-2'
										: ''}"
									onclick={() =>
										(lightbox = {
											images: chapter.photos,
											index: i,
											name: chapterTitle(chapter)
										})}
								>
									<img
										src={photo.image}
										alt=""
										loading="lazy"
										class="h-full w-full object-cover transition-transform duration-500 hover:scale-105"
									/>
								</button>
							{/each}
						</div>
					{/if}
				</section>
			{/each}
		</div>

		<footer data-chapter="" class="border-t border-base-300 bg-base-200/60">
			<div class="flex flex-col items-center gap-4 px-5 py-12 text-center">
				<p class="text-2xl font-bold">{$t('story.the_end')}</p>
				{#if shareUrl}
					<p class="text-base-content/70">{$t('story.share_prompt')}</p>
					<div class="flex flex-wrap justify-center gap-2">
						{#if canNativeShare}
							<button type="button" class="btn btn-primary gap-1" onclick={nativeShare}>
								<ShareVariant class="h-4 w-4" />
								{$t('story.share')}
							</button>
						{/if}
						<button type="button" class="btn gap-1" onclick={copyShareLink}>
							<ContentCopy class="h-4 w-4" />
							{$t('share.copy_link')}
						</button>
					</div>
				{/if}
				<p class="text-xs text-base-content/50">{$t('story.made_with')}</p>
			</div>
		</footer>
	</div>

	{#if mounted && isWide && hasMap}
		<aside class="relative hidden min-h-0 flex-1 border-l border-base-300 lg:block">
			{@render map('h-full w-full')}
		</aside>
	{/if}
</article>
