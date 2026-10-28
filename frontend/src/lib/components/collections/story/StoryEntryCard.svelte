<script lang="ts">
	import { t } from 'svelte-i18n';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	import type { ContentImage } from '#lib/types.js';
	import type { StoryEntry } from '#lib/collections/story.js';
	import {
		formatDisplayDate,
		formatDisplayDateTime,
		formatDisplayTime,
		type DateFormatPreference
	} from '#lib/dateFormat.js';
	import { getTransportIcon } from '#lib/calendar/events.js';
	import { LODGING_TYPES_ICONS } from '#lib';
	import OpenInNew from '~icons/mdi/open-in-new';
	import MapMarker from '~icons/mdi/map-marker-outline';
	import Star from '~icons/mdi/star';
	import CheckCircle from '~icons/mdi/check-circle';
	import CheckboxMarked from '~icons/mdi/checkbox-marked-outline';
	import CheckboxBlank from '~icons/mdi/checkbox-blank-outline';
	import Paperclip from '~icons/mdi/paperclip';

	interface Props {
		entry: StoryEntry;
		dateFormat: DateFormatPreference;
		color: string;
		pinLabel?: string | null;
		active?: boolean;
		onPhotos?: (images: ContentImage[], index: number, name: string) => void;
	}

	let { entry, dateFormat, color, pinLabel = null, active = false, onPhotos }: Props = $props();

	const DESCRIPTION_COLLAPSE_CHARS = 420;
	let expanded = $state(false);

	function markdown(text: string | null | undefined): string {
		return text ? DOMPurify.sanitize(marked(text) as string) : '';
	}

	function clock(value: string | null | undefined) {
		return value ? formatDisplayTime(value, dateFormat) : '';
	}

	function duration(value: string | null | undefined): string {
		if (!value) return '';
		const match = /^(?:(\d+) )?(\d{1,2}):(\d{2}):(\d{2})/.exec(value);
		if (!match) return '';
		const hours = Number(match[1] ?? 0) * 24 + Number(match[2]);
		const minutes = Number(match[3]);
		return hours ? `${hours} h ${minutes} min` : `${minutes} min`;
	}

	function km(meters: number | null | undefined) {
		return meters ? `${(meters / 1000).toFixed(1)} km` : '';
	}

	function money(amount: number | null | undefined, currency: string | null | undefined) {
		if (amount === null || amount === undefined) return '';
		try {
			return new Intl.NumberFormat(undefined, {
				style: 'currency',
				currency: currency || 'USD'
			}).format(Number(amount));
		} catch {
			return `${amount} ${currency ?? ''}`.trim();
		}
	}

	let images = $derived(
		entry.kind === 'location' || (entry.kind === 'lodging' && !entry.continued)
			? (entry.object.images ?? []).filter((image) => image?.image)
			: []
	);
	let mosaic = $derived(images.slice(0, 4));
	let description = $derived(
		entry.kind === 'location' || entry.kind === 'lodging' || entry.kind === 'transportation'
			? (entry.object.description ?? '')
			: entry.kind === 'note'
				? (entry.object.content ?? '')
				: ''
	);
	let longDescription = $derived(description.length > DESCRIPTION_COLLAPSE_CHARS);
	let timeLabel = $derived.by(() => {
		const item = entry.item;
		if (!item?.start_time) return '';
		const start = clock(item.start_time);
		return item.end_time ? `${start} – ${clock(item.end_time)}` : start;
	});
	let attachments = $derived(
		entry.kind === 'location' || entry.kind === 'lodging' || entry.kind === 'transportation'
			? ((entry.object as { attachments?: { id: string; file: string; name?: string }[] })
					.attachments ?? [])
			: []
	);
</script>

<article
	id={`story-${entry.key}`}
	class="story-entry relative rounded-2xl border bg-base-100 transition-shadow {active
		? 'border-primary shadow-lg'
		: 'border-base-300 shadow-sm'}"
>
	{#if mosaic.length > 0}
		<div
			class="grid gap-0.5 overflow-hidden rounded-t-2xl {mosaic.length === 1
				? 'grid-cols-1'
				: 'grid-cols-2'}"
		>
			{#each mosaic as image, i (image.id ?? image.image)}
				<button
					type="button"
					class="relative overflow-hidden bg-base-200 {mosaic.length === 1
						? 'aspect-[16/9]'
						: mosaic.length === 3 && i === 0
							? 'row-span-2 aspect-auto h-full'
							: 'aspect-[4/3]'}"
					aria-label={$t('story.open_photo', { values: { name: entry.object.name } })}
					onclick={() => onPhotos?.(images, i, entry.object.name)}
				>
					<img
						src={image.image}
						alt=""
						loading="lazy"
						class="h-full w-full object-cover transition-transform duration-500 hover:scale-105"
					/>
					{#if i === mosaic.length - 1 && images.length > mosaic.length}
						<span
							class="absolute inset-0 flex items-center justify-center bg-black/45 text-xl font-semibold text-white"
						>
							+{images.length - mosaic.length}
						</span>
					{/if}
				</button>
			{/each}
		</div>
	{/if}

	<div class="space-y-2 p-4 sm:p-5">
		<div class="flex items-start gap-3">
			{#if pinLabel}
				<span
					class="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white"
					style="background-color: {color}"
					aria-hidden="true"
				>
					{pinLabel}
				</span>
			{/if}
			<div class="min-w-0 flex-1">
				<div class="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-base-content/60">
					{#if entry.kind === 'lodging'}
						<span>
							{LODGING_TYPES_ICONS[entry.object.type as keyof typeof LODGING_TYPES_ICONS] ?? '🏨'}
							{entry.continued ? $t('story.still_staying') : $t('story.stay')}
						</span>
					{:else if entry.kind === 'transportation'}
						<span>{getTransportIcon(entry.object.type)} {entry.object.type}</span>
					{:else if entry.kind === 'activity'}
						<span>🥾 {entry.object.sport_type}</span>
					{:else if entry.kind === 'trail'}
						<span>🧭 {$t('story.trail')}</span>
					{:else if entry.kind === 'note'}
						<span>📝 {$t('story.note')}</span>
					{:else if entry.kind === 'checklist'}
						<span>✅ {$t('story.checklist')}</span>
					{/if}
					{#if timeLabel}
						<span class="badge badge-ghost badge-sm">{timeLabel}</span>
					{/if}
					{#if entry.item?.is_optional}
						<span class="badge badge-outline badge-sm">{$t('story.optional')}</span>
					{/if}
					{#if entry.kind === 'location' && entry.object.is_visited}
						<span class="badge badge-success badge-sm gap-1">
							<CheckCircle class="h-3 w-3" />
							{$t('story.visited')}
						</span>
					{/if}
				</div>
				<h3 class="mt-0.5 text-lg font-semibold leading-snug sm:text-xl">{entry.object.name}</h3>

				{#if entry.kind === 'location'}
					{#if entry.object.location}
						<p class="mt-1 flex items-start gap-1 text-sm text-base-content/70">
							<MapMarker class="mt-0.5 h-4 w-4 shrink-0" />
							<span>{entry.object.location}</span>
						</p>
					{/if}
					{#if entry.object.rating}
						<p
							class="mt-1 flex items-center gap-0.5 text-warning"
							aria-label={`${entry.object.rating}/5`}
						>
							{#each Array(Math.round(entry.object.rating)) as _}
								<Star class="h-4 w-4" />
							{/each}
						</p>
					{/if}
				{:else if entry.kind === 'lodging' && !entry.continued}
					<p class="mt-1 text-sm text-base-content/70">
						{#if entry.object.check_in}
							{formatDisplayDate(entry.object.check_in, dateFormat)}
						{/if}
						{#if entry.object.check_out}
							→ {formatDisplayDate(entry.object.check_out, dateFormat)}
						{/if}
					</p>
					{#if entry.object.location}
						<p class="flex items-start gap-1 text-sm text-base-content/70">
							<MapMarker class="mt-0.5 h-4 w-4 shrink-0" />
							<span>{entry.object.location}</span>
						</p>
					{/if}
					{#if entry.object.reservation_number}
						<p class="text-sm">{$t('story.confirmation')}: {entry.object.reservation_number}</p>
					{/if}
					{#if entry.object.price !== null && entry.object.price !== undefined}
						<p class="text-sm">{money(entry.object.price, entry.object.price_currency)}</p>
					{/if}
				{:else if entry.kind === 'transportation'}
					{@const leg = entry.object}
					{#if leg.from_location || leg.to_location}
						<p class="mt-1 text-sm font-medium">
							{leg.from_location || leg.start_code || '…'} → {leg.to_location ||
								leg.end_code ||
								'…'}
						</p>
					{/if}
					<p class="text-sm text-base-content/70">
						{#if leg.date}
							{formatDisplayDateTime(leg.date, dateFormat, leg.start_timezone)}
						{/if}
						{#if leg.end_date}
							→ {formatDisplayDateTime(
								leg.end_date,
								dateFormat,
								leg.end_timezone || leg.start_timezone
							)}
						{/if}
					</p>
					{#if leg.flight_number}
						<p class="text-sm">{$t('story.flight')}: {leg.flight_number}</p>
					{/if}
					{#if leg.price !== null && leg.price !== undefined}
						<p class="text-sm">{money(leg.price, leg.price_currency)}</p>
					{/if}
				{:else if entry.kind === 'activity'}
					{@const activity = entry.object}
					<div class="mt-2 flex flex-wrap gap-2">
						{#if activity.distance}
							<span class="badge badge-lg badge-ghost">{km(activity.distance)}</span>
						{/if}
						{#if activity.elevation_gain}
							<span class="badge badge-lg badge-ghost"
								>↑ {Math.round(activity.elevation_gain)} m</span
							>
						{/if}
						{#if duration(activity.moving_time)}
							<span class="badge badge-lg badge-ghost">⏱ {duration(activity.moving_time)}</span>
						{/if}
					</div>
				{:else if entry.kind === 'checklist'}
					{#if entry.object.items?.length}
						<ul class="mt-2 space-y-1">
							{#each entry.object.items as item (item.id)}
								<li class="flex items-center gap-2 text-sm">
									{#if item.is_checked}
										<CheckboxMarked class="h-4 w-4 text-success" />
									{:else}
										<CheckboxBlank class="h-4 w-4 opacity-60" />
									{/if}
									<span class={item.is_checked ? 'line-through opacity-60' : ''}>{item.name}</span>
								</li>
							{/each}
						</ul>
					{/if}
				{/if}
			</div>
		</div>

		{#if description}
			<div class="relative">
				<div
					class="prose prose-sm max-w-none sm:prose-base {longDescription && !expanded
						? 'max-h-40 overflow-hidden'
						: ''}"
				>
					{@html markdown(description)}
				</div>
				{#if longDescription && !expanded}
					<div
						class="pointer-events-none absolute inset-x-0 bottom-0 h-12 bg-gradient-to-t from-base-100"
					></div>
				{/if}
			</div>
			{#if longDescription}
				<button
					type="button"
					class="btn btn-link btn-sm px-0"
					onclick={() => (expanded = !expanded)}
				>
					{expanded ? $t('story.show_less') : $t('story.read_more')}
				</button>
			{/if}
		{/if}

		{#if entry.kind === 'note' && entry.object.links?.length}
			<ul class="space-y-1">
				{#each entry.object.links as link (link)}
					<li>
						<a
							class="link link-primary break-all text-sm"
							href={link}
							target="_blank"
							rel="noopener noreferrer">{link}</a
						>
					</li>
				{/each}
			</ul>
		{/if}

		{#if attachments.length}
			<ul class="flex flex-wrap gap-2">
				{#each attachments as file (file.id)}
					<li>
						<a
							class="btn btn-ghost btn-xs gap-1"
							href={file.file}
							target="_blank"
							rel="noopener noreferrer"
						>
							<Paperclip class="h-3.5 w-3.5" />
							{file.name || $t('story.attachment')}
						</a>
					</li>
				{/each}
			</ul>
		{/if}

		{#if (entry.kind === 'location' || (entry.kind === 'lodging' && !entry.continued)) && entry.object.link}
			<a
				class="btn btn-outline btn-sm gap-1"
				href={entry.object.link}
				target="_blank"
				rel="noopener noreferrer"
			>
				<OpenInNew class="h-4 w-4" />
				{$t('story.visit_website')}
			</a>
		{:else if entry.kind === 'trail' && (entry.object.link || entry.object.wanderer_link)}
			<a
				class="btn btn-outline btn-sm gap-1"
				href={entry.object.link || entry.object.wanderer_link}
				target="_blank"
				rel="noopener noreferrer"
			>
				<OpenInNew class="h-4 w-4" />
				{$t('story.open_trail')}
			</a>
		{/if}
	</div>
</article>
