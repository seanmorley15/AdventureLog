<script lang="ts">
	import { t } from 'svelte-i18n';
	import CloseIcon from '~icons/mdi/close';
	import MapMarkerIcon from '~icons/mdi/map-marker';
	import ClockIcon from '~icons/mdi/clock';
	import OpenInNew from '~icons/mdi/open-in-new';
	import FolderIcon from '~icons/mdi/folder';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	import type { CalendarDisplayEvent } from '$lib/calendar/types';

	export let show = false;
	export let event: CalendarDisplayEvent | null = null;
	export let onClose: () => void;
	export let timezoneMode: 'event' | 'local' = 'event';
	export let userTimezone = '';

	const renderMarkdown = (markdown: string) => DOMPurify.sanitize(marked(markdown) as string);

	$: detailUrl = event?.extendedProps?.url || '';
	$: typeLabel = event?.extendedProps?.type
		? $t(`calendar.type_${event.extendedProps.type}`)
		: $t('calendar.event');
</script>

{#if show && event}
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<div class="modal modal-open">
		<div
			class="modal-box max-w-3xl p-0 bg-base-100 border border-base-300 shadow-2xl max-h-[90vh] flex flex-col"
		>
			<div
				class="relative bg-gradient-to-r from-primary via-primary/85 to-secondary/75 text-primary-content p-6"
			>
				<div class="relative flex items-start justify-between gap-4">
					<div class="flex items-start gap-4 min-w-0">
						<div
							class="h-14 w-14 rounded-2xl bg-base-100/20 backdrop-blur flex items-center justify-center text-3xl shadow-inner shrink-0"
						>
							{event.extendedProps?.icon || '📅'}
						</div>
						<div class="space-y-1 min-w-0">
							<p class="text-xs uppercase tracking-wide font-semibold opacity-80">{typeLabel}</p>
							<h3 class="text-2xl font-bold leading-tight truncate">
								{event.extendedProps?.adventureName || event.title}
							</h3>
							<div class="flex flex-wrap gap-2 mt-2">
								{#if event.extendedProps?.category}
									<span class="badge badge-lg bg-base-100/20 text-base-100 border-0">
										{event.extendedProps.category}
									</span>
								{/if}
								{#if event.extendedProps?.collectionName}
									<span
										class="badge badge-lg bg-base-100/10 text-base-100 border-base-100/20 gap-1"
									>
										<FolderIcon class="w-3.5 h-3.5" />
										{event.extendedProps.collectionName}
									</span>
								{/if}
							</div>
						</div>
					</div>
					<button class="btn btn-ghost btn-sm btn-circle shrink-0" on:click={onClose}>
						<CloseIcon class="w-5 h-5" />
					</button>
				</div>
			</div>

			<div class="p-6 space-y-5 overflow-y-auto">
				<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
					<div class="card bg-base-200/60 border border-base-300/70">
						<div class="card-body p-4">
							<div class="flex items-start gap-3">
								<ClockIcon class="w-6 h-6 text-primary shrink-0" />
								<div>
									<div class="font-semibold">
										{#if event.extendedProps?.isAllDay}
											{$t('calendar.all_day_event')}
										{:else}
											{event.extendedProps.formattedStart}
											{#if event.extendedProps.formattedEnd !== event.extendedProps.formattedStart}
												→ {event.extendedProps.formattedEnd}
											{/if}
										{/if}
									</div>
									<div class="text-xs text-base-content/70 mt-1">
										{event.extendedProps?.timezoneLabel ||
											(timezoneMode === 'local'
												? `${$t('calendar.your timezone')} (${userTimezone})`
												: `${$t('calendar.event timezone')} (${event.extendedProps?.timezone || userTimezone})`)}
									</div>
								</div>
							</div>
						</div>
					</div>

					{#if event.extendedProps?.location}
						<div class="card bg-base-200/60 border border-base-300/70">
							<div class="card-body p-4">
								<div class="flex items-start gap-3">
									<MapMarkerIcon class="w-6 h-6 text-primary shrink-0" />
									<div>
										<div class="font-semibold">{event.extendedProps.location}</div>
										{#if event.extendedProps.route}
											<div class="text-sm text-base-content/70">{event.extendedProps.route}</div>
										{/if}
									</div>
								</div>
							</div>
						</div>
					{/if}
				</div>

				{#if event.extendedProps?.description}
					<div class="card bg-base-200/60 border border-base-300/70">
						<div class="card-body p-4">
							<div class="font-semibold mb-2">{$t('adventures.description')}</div>
							<article class="prose max-w-none prose-sm">
								{@html renderMarkdown(event.extendedProps.description)}
							</article>
						</div>
					</div>
				{/if}

				<div class="flex flex-wrap items-center justify-between gap-3 pt-2">
					<div class="flex flex-wrap gap-2">
						{#if detailUrl}
							<a href={detailUrl} class="btn btn-primary btn-sm gap-2">
								<OpenInNew class="w-4 h-4" />
								{$t('map.view_details')}
							</a>
						{/if}
						{#if event.extendedProps?.collectionId}
							<a
								href={`/collections/${event.extendedProps.collectionId}`}
								class="btn btn-ghost btn-sm gap-2"
							>
								<FolderIcon class="w-4 h-4" />
								{$t('calendar.view_collection')}
							</a>
						{/if}
					</div>
					<button class="btn btn-ghost btn-sm" on:click={onClose}>{$t('about.close')}</button>
				</div>
			</div>
		</div>
		<!-- svelte-ignore a11y-click-events-have-key-events -->
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<div class="modal-backdrop" on:click={onClose}></div>
	</div>
{/if}
