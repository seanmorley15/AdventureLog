<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import MarkdownEditor from './MarkdownEditor.svelte';
	import { addToast } from '$lib/toasts';
	import { copyToClipboard } from '$lib/index';
	import type { Collection, ContentImage, SlimCollection } from '$lib/types';
	import DateInput from './shared/DateInput.svelte';
	import { addDays, browserTimezone } from '$lib/dayPlan';
	import { formatDisplayDate } from '$lib/dateFormat';

	// Icons
	import CollectionIcon from '~icons/mdi/folder-multiple';
	import InfoIcon from '~icons/mdi/information';
	import CalendarIcon from '~icons/mdi/calendar';
	import LinkIcon from '~icons/mdi/link';
	import SaveIcon from '~icons/mdi/content-save';
	import CloseIcon from '~icons/mdi/close';
	import ImageIcon from '~icons/mdi/image-multiple';

	const dispatch = createEventDispatcher();
	let modal: HTMLDialogElement;

	interface Props {
		collectionToEdit?: Collection | SlimCollection | null;
	}

	let { collectionToEdit = null }: Props = $props();

	let collection: Collection = $state({
		id: '',
		name: '',
		description: '',
		start_date: null,
		end_date: null,
		type: 'folder',
		user: '',
		is_public: false,
		locations: [],
		link: '',
		shared_with: [],
		itinerary: [],
		status: null,
		days_until_start: null,
		primary_image: null,
		primary_image_id: null,
		itinerary_days: []
	});

	let coverImageId: string | null = $state(null);
	let showCoverGrid = $state(false);
	let planMode = $state<'dates' | 'days'>('dates');
	let dayCount = $state<number | null>(null);

	// A day-based trip is edited by day count; a date-keyed trip keeps its dates until "Plan by days".
	const editingDayPlan = $derived(Boolean(collectionToEdit?.day_count));
	const canChoosePlanMode = $derived(!editingDayPlan && collectionToEdit?.type !== 'trip');
	const convertingFolder = $derived(
		collectionToEdit?.type === 'folder' && collection.type === 'trip'
	);
	const convertingToFolder = $derived(
		collectionToEdit?.type === 'trip' && collection.type === 'folder'
	);
	const usesDayCount = $derived(collection.type === 'trip' && planMode === 'days');
	const derivedEndDate = $derived(
		usesDayCount && collection.start_date && dayCount && dayCount > 0
			? addDays(collection.start_date, dayCount - 1)
			: null
	);
	let availableImages = $derived(coverCandidates(collectionToEdit));
	let previousCollectionId: string | null | undefined = undefined;

	function coverCandidates(source: Collection | SlimCollection | null): ContentImage[] {
		if (!source) return [];

		const pooled: ContentImage[] = [];
		if ('locations' in source && source.locations?.length) {
			for (const loc of source.locations) {
				if (loc.images?.length) pooled.push(...loc.images);
			}
		}
		if (pooled.length === 0 && 'location_images' in source && source.location_images?.length) {
			pooled.push(...source.location_images);
		}

		const deduped: ContentImage[] = [];
		for (const img of pooled) {
			if (!img?.id || !img.image || deduped.some((existing) => existing.id === img.id)) continue;
			deduped.push(img);
		}

		deduped.sort((a, b) => {
			if (a.is_primary && !b.is_primary) return -1;
			if (!a.is_primary && b.is_primary) return 1;
			return a.id.localeCompare(b.id);
		});
		return deduped;
	}

	$effect.pre(() => {
		const sourceId = collectionToEdit?.id ?? null;
		if (sourceId === previousCollectionId) return;

		previousCollectionId = sourceId;
		const locations =
			collectionToEdit && 'locations' in collectionToEdit ? collectionToEdit.locations || [] : [];
		const carriedCoverId =
			collectionToEdit?.primary_image?.id ??
			(collectionToEdit && 'primary_image_id' in collectionToEdit
				? (collectionToEdit.primary_image_id ?? null)
				: null);
		collection = {
			id: collectionToEdit?.id || '',
			name: collectionToEdit?.name || '',
			description: collectionToEdit?.description || '',
			start_date: collectionToEdit?.start_date || null,
			end_date: collectionToEdit?.end_date || null,
			type:
				collectionToEdit?.type ||
				(collectionToEdit?.start_date && collectionToEdit?.end_date ? 'trip' : 'folder'),
			user: collectionToEdit?.user || '',
			is_public: collectionToEdit?.is_public || false,
			locations,
			link: collectionToEdit?.link || '',
			shared_with: collectionToEdit?.shared_with || [],
			itinerary:
				collectionToEdit && 'itinerary' in collectionToEdit ? collectionToEdit.itinerary || [] : [],
			status: collectionToEdit?.status ?? null,
			days_until_start: collectionToEdit?.days_until_start ?? null,
			primary_image: collectionToEdit?.primary_image ?? null,
			primary_image_id: carriedCoverId,
			itinerary_days: []
		};
		coverImageId = collection.primary_image?.id || collection.primary_image_id || null;
		dayCount = collectionToEdit?.day_count ?? null;
		planMode = collectionToEdit?.day_count ? 'days' : 'dates';
	});

	function selectCover(imageId: string | null) {
		coverImageId = imageId;
		collection.primary_image_id = imageId;
	}

	function toSlimCollection(col: Collection): SlimCollection {
		return {
			id: col.id,
			user: col.user,
			name: col.name,
			description: col.description,
			is_public: col.is_public,
			start_date: col.start_date,
			end_date: col.end_date,
			type: col.type,
			timezone: col.timezone,
			day_count: col.day_count ?? null,
			is_archived: col.is_archived ?? false,
			link: col.link ?? null,
			created_at: col.created_at ?? '',
			updated_at: col.updated_at ?? '',
			location_images: (() => {
				const fromLocations = (col.locations || []).flatMap((loc) => loc.images || []);
				return fromLocations.length > 0 ? fromLocations : availableImages;
			})(),
			location_count: (col.locations || []).length,
			shared_with: col.shared_with || [],
			status: col.status ?? null,
			days_until_start: col.days_until_start ?? null,
			primary_image: col.primary_image ?? null
		};
	}

	onMount(() => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}
		// Paint the form first. Cover photos are already on the card payload.
		requestAnimationFrame(() => {
			showCoverGrid = true;
		});
	});

	function close() {
		dispatch('close');
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			close();
		}
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();

		if (!collection.start_date) {
			collection.start_date = null;
		}
		if (!collection.end_date) {
			collection.end_date = null;
		}

		if (convertingToFolder && !window.confirm($t('collection.convert_to_folder_warning'))) {
			return;
		}

		const dayCountOptional = convertingFolder && !collectionToEdit?.day_count;
		if (usesDayCount && !dayCountOptional) {
			if (!dayCount || dayCount < 1) {
				addToast('error', $t('collection.day_count_required'));
				return;
			}
		} else if (usesDayCount && dayCount && dayCount < 1) {
			addToast('error', $t('collection.day_count_required'));
			return;
		} else if (
			collection.type === 'trip' &&
			!usesDayCount &&
			!convertingFolder &&
			(!collection.start_date || !collection.end_date)
		) {
			addToast('error', $t('adventures.trip_requires_dates'));
			return;
		}

		if (
			!usesDayCount &&
			collection.start_date &&
			collection.end_date &&
			collection.start_date > collection.end_date
		) {
			addToast('error', $t('adventures.start_before_end_error'));
			return;
		}

		const payload: any = {
			name: collection.name,
			description: collection.description,
			start_date: collection.start_date,
			type: collection.type,
			is_public: collection.is_public,
			link: collection.link,
			primary_image_id: coverImageId
		};
		if (usesDayCount && dayCount) {
			payload.day_count = dayCount;
		} else if (!usesDayCount) {
			payload.end_date = collection.end_date;
		}
		const anchorChanged = collection.start_date !== (collectionToEdit?.start_date ?? null);
		if (collection.type === 'trip' && collection.start_date && anchorChanged) {
			payload.timezone = browserTimezone();
		}

		// Clean up link: empty/whitespace → null, invalid URL → null
		if (!payload.link || !payload.link.trim()) {
			payload.link = null;
		} else {
			try {
				new URL(payload.link);
			} catch {
				payload.link = null;
			}
		}

		if (collection.id === '') {
			let res = await fetch('/api/collections', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(payload)
			});
			let data = await res.json();
			if (data.id) {
				collection = data as Collection;
				coverImageId = collection.primary_image?.id ?? null;
				collection.primary_image_id = coverImageId;
				addToast('success', $t('collection.collection_created'));
				dispatch('save', toSlimCollection(collection));
			} else {
				console.error(data);
				// Extract field-level errors from Django response
				const fieldErrors = Object.entries(data)
					.filter(([_, v]) => Array.isArray(v))
					.map(([k, v]) => `${k}: ${(v as string[]).join(', ')}`)
					.join('; ');
				addToast('error', fieldErrors || $t('collection.error_creating_collection'));
			}
		} else {
			let res = await fetch(`/api/collections/${collection.id}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(payload)
			});
			let data = await res.json();
			if (data.id) {
				collection = data as Collection;
				coverImageId = collection.primary_image?.id ?? null;
				collection.primary_image_id = coverImageId;
				addToast('success', $t('collection.collection_edit_success'));
				dispatch('save', toSlimCollection(collection));
			} else {
				// Extract field-level errors from Django response
				const fieldErrors = Object.entries(data)
					.filter(([_, v]) => Array.isArray(v))
					.map(([k, v]) => `${k}: ${(v as string[]).join(', ')}`)
					.join('; ');
				addToast('error', fieldErrors || $t('collection.error_editing_collection'));
			}
		}
	}
</script>

<dialog id="my_modal_1" class="modal backdrop-blur-xs">
	<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<div
		class="modal-box w-11/12 max-w-6xl bg-gradient-to-br from-base-100 via-base-100 to-base-200 border border-base-300 shadow-2xl max-h-[85vh] flex flex-col"
		role="dialog"
		onkeydown={handleKeydown}
		tabindex="0"
	>
		<!-- Header Section -->
		<div
			class="top-0 z-10 bg-base-100/90 backdrop-blur-lg border-b border-base-300 -mx-6 -mt-6 px-6 py-4 mb-6"
		>
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-3">
					<div class="p-2 bg-primary/10 rounded-xl">
						<CollectionIcon class="w-8 h-8 text-primary" />
					</div>
					<div>
						<h1 class="text-3xl font-bold text-primary bg-clip-text">
							{collectionToEdit
								? $t('adventures.edit_collection')
								: $t('collection.new_collection')}
						</h1>
						<p class="text-sm text-base-content/80">
							{collectionToEdit
								? $t('collection.update_collection_details')
								: $t('collection.create_new_collection')}
						</p>
					</div>
				</div>

				<!-- Close Button -->
				<button class="btn btn-ghost btn-square" onclick={close}>
					<CloseIcon class="w-5 h-5" />
				</button>
			</div>
		</div>

		<!-- Main Content -->
		<div class="p-6 overflow-auto max-h-[70vh]">
			<form method="post" onsubmit={handleSubmit} class="space-y-6">
				<!-- Basic Information Section -->
				<div class="card bg-base-100 border border-base-300 shadow-lg">
					<div class="card-body p-6">
						<div class="flex items-center gap-3 mb-6">
							<div class="p-2 bg-primary/10 rounded-lg">
								<InfoIcon class="w-5 h-5 text-primary" />
							</div>
							<h2 class="text-xl font-bold">{$t('adventures.basic_information')}</h2>
						</div>

						<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
							<!-- Left Column -->
							<div class="space-y-4">
								<!-- Name Field -->
								<div class="flex flex-col">
									<label class="field-label" for="name">
										{$t('adventures.name')}<span class="text-error ml-1">*</span>
									</label>
									<input
										type="text"
										id="name"
										name="name"
										bind:value={collection.name}
										class="input w-full"
										placeholder={$t('collection.enter_collection_name')}
										required
									/>
								</div>

								<!-- Description Field -->
								<div class="flex flex-col">
									<label class="field-label" for="description">{$t('adventures.description')}</label
									>
									<MarkdownEditor bind:text={collection.description} editor_height={'h-32'} />
								</div>

								<!-- Link Field -->
								<div class="flex flex-col">
									<label class="field-label flex items-center gap-2" for="link">
										<LinkIcon class="w-4 h-4" />
										{$t('adventures.link')}
									</label>
									<input
										type="text"
										id="link"
										name="link"
										bind:value={collection.link}
										class="input w-full"
										placeholder="https://example.com"
									/>
								</div>
							</div>

							<!-- Right Column -->
							<div class="space-y-4">
								<div class="flex flex-col gap-2">
									<span class="field-label" id="collection-type-label">
										{$t('adventures.collection_type')}
									</span>
									<div
										class="join w-full"
										role="radiogroup"
										aria-labelledby="collection-type-label"
									>
										<button
											type="button"
											class="btn join-item flex-1 {collection.type === 'trip' ? 'btn-primary' : ''}"
											aria-pressed={collection.type === 'trip'}
											onclick={() => (collection.type = 'trip')}
										>
											{$t('adventures.trip')}
										</button>
										<button
											type="button"
											class="btn join-item flex-1 {collection.type === 'folder'
												? 'btn-primary'
												: ''}"
											aria-pressed={collection.type === 'folder'}
											onclick={() => (collection.type = 'folder')}
										>
											{$t('adventures.folder')}
										</button>
									</div>
									<p class="field-hint">
										{collection.type === 'trip'
											? $t('adventures.trip_type_hint')
											: $t('adventures.folder_type_hint')}
									</p>
									{#if convertingToFolder}
										<div class="alert alert-warning py-2 text-sm">
											{$t('collection.convert_to_folder_warning')}
										</div>
									{/if}
									{#if convertingFolder && !collectionToEdit?.day_count}
										<p class="field-hint">{$t('collection.folder_to_trip_hint')}</p>
									{/if}
								</div>

								{#if collection.type === 'trip' && canChoosePlanMode}
									<div class="flex flex-col gap-2">
										<span class="field-label" id="plan-mode-label">{$t('collection.plan_by')}</span>
										<div class="join w-full" role="radiogroup" aria-labelledby="plan-mode-label">
											<button
												type="button"
												class="btn btn-sm join-item flex-1 {planMode === 'dates'
													? 'btn-primary'
													: ''}"
												aria-pressed={planMode === 'dates'}
												onclick={() => (planMode = 'dates')}
											>
												{$t('collection.plan_by_dates')}
											</button>
											<button
												type="button"
												class="btn btn-sm join-item flex-1 {planMode === 'days'
													? 'btn-primary'
													: ''}"
												aria-pressed={planMode === 'days'}
												onclick={() => (planMode = 'days')}
											>
												{$t('collection.plan_by_day_count')}
											</button>
										</div>
									</div>
								{/if}

								{#if usesDayCount}
									<div class="flex flex-col">
										<label class="field-label" for="day_count">
											{$t('collection.day_count')}
											{#if !(convertingFolder && !collectionToEdit?.day_count)}
												<span class="text-error ml-1">*</span>
											{/if}
										</label>
										<input
											type="number"
											id="day_count"
											name="day_count"
											class="input w-full"
											min="1"
											bind:value={dayCount}
											required={!(convertingFolder && !collectionToEdit?.day_count)}
										/>
										<p class="field-hint">
											{$t('collection.day_count_hint')}
										</p>
									</div>
								{/if}

								<!-- Start Date -->
								<div class="flex flex-col">
									<label class="field-label flex items-center gap-2" for="start_date">
										<CalendarIcon class="w-4 h-4" />
										{usesDayCount
											? $t('itinerary.start_date_optional')
											: $t('adventures.start_date')}
										{#if collection.type === 'trip' && !usesDayCount && !convertingFolder}
											<span class="text-error">*</span>
										{/if}
									</label>
									<DateInput
										id="start_date"
										name="start_date"
										bind:value={collection.start_date}
										clearable={true}
									/>
									{#if derivedEndDate}
										<p class="field-hint">
											{$t('collection.ends_on', {
												values: { date: formatDisplayDate(derivedEndDate) }
											})}
										</p>
									{/if}
								</div>

								{#if !usesDayCount}
									<!-- End Date -->
									<div class="flex flex-col">
										<label class="field-label flex items-center gap-2" for="end_date">
											<CalendarIcon class="w-4 h-4" />
											{$t('adventures.end_date')}
											{#if collection.type === 'trip'}
												<span class="text-error">*</span>
											{/if}
										</label>
										<DateInput
											id="end_date"
											name="end_date"
											bind:value={collection.end_date}
											clearable={true}
										/>
									</div>
								{/if}

								<!-- Public Toggle -->
								<div class="flex flex-col">
									<label class="field-toggle">
										<input
											type="checkbox"
											class="toggle toggle-primary"
											id="is_public"
											name="is_public"
											bind:checked={collection.is_public}
										/>
										<span>
											<span class="font-semibold text-base-content"
												>{$t('collection.public_collection')}</span
											>
											<p class="field-hint">{$t('collection.public_collection_description')}</p>
										</span>
									</label>
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- Date Warning Alert -->
				{#if collection.type === 'folder' && !collection.start_date && !collection.end_date}
					<div role="alert" class="alert alert-info shadow-lg">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							class="h-6 w-6 shrink-0 stroke-current"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
							></path>
						</svg>
						<span>{$t('adventures.collection_no_start_end_date')}</span>
					</div>
				{:else if editingDayPlan && collection.start_date !== (collectionToEdit?.start_date ?? null)}
					<div role="alert" class="alert alert-info shadow-lg">
						<CalendarIcon class="h-6 w-6 shrink-0" />
						<span>{$t('collection.day_plan_date_hint')}</span>
					</div>
				{:else if !editingDayPlan && collection.id && collectionToEdit?.start_date && collectionToEdit?.end_date && (collection.start_date !== collectionToEdit.start_date || collection.end_date !== collectionToEdit.end_date)}
					<div role="alert" class="alert alert-warning shadow-lg">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							class="stroke-current shrink-0 h-6 w-6"
							fill="none"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
							/>
						</svg>
						<div>
							<div class="font-bold">{$t('collection.changing_date_title')}</div>
							<div class="text-sm">
								{$t('collection.changing_date_warning')}
							</div>
						</div>
					</div>
				{/if}

				<!-- Cover Image Selection -->
				{#if collection.id}
					<div class="card bg-base-100 border border-base-300 shadow-lg">
						<div class="card-body p-6 space-y-4">
							<div class="flex items-center gap-3">
								<div class="p-2 bg-primary/10 rounded-lg">
									<ImageIcon class="w-5 h-5 text-primary" />
								</div>
								<div>
									<h3 class="text-lg font-semibold">
										{$t('collection.cover_image') ?? 'Cover image'}
									</h3>
									<p class="text-sm text-base-content/60">
										{$t('collection.cover_image_hint') ??
											'Choose a cover from images in this collection.'}
									</p>
								</div>
							</div>

							{#if availableImages.length === 0}
								<div class="alert alert-info shadow-xs">
									<span>
										{$t('collection.no_images_available') ??
											'No images available from linked locations yet.'}
									</span>
								</div>
							{:else if !showCoverGrid}
								<div class="h-32 rounded-xl bg-base-200/60"></div>
							{:else}
								<div
									class="grid max-h-80 grid-cols-2 gap-3 overflow-y-auto sm:grid-cols-3 lg:grid-cols-4"
								>
									{#each availableImages as image (image.id)}
										<button
											type="button"
											class="relative group rounded-xl overflow-hidden border border-base-300 bg-base-200/30 hover:border-primary transition shadow-xs {coverImageId ===
											image.id
												? 'ring-2 ring-primary ring-offset-2 ring-offset-base-100'
												: ''}"
											onclick={() => selectCover(image.id)}
											aria-pressed={coverImageId === image.id}
										>
											<img
												src={image.image}
												alt=""
												loading="lazy"
												decoding="async"
												class="h-24 w-full object-cover"
											/>
											<div
												class="absolute inset-0 bg-gradient-to-t from-base-300/60 to-transparent opacity-0 group-hover:opacity-100 transition"
											></div>
											{#if coverImageId === image.id}
												<div class="absolute top-2 left-2 badge badge-primary gap-2 shadow-sm">
													{$t('collection.cover') ?? 'Cover'}
												</div>
											{:else if image.is_primary}
												<div class="absolute top-2 left-2 badge badge-ghost shadow-sm">
													{$t('collection.location_primary') ?? 'Location cover'}
												</div>
											{/if}
											<div
												class="absolute bottom-2 right-2 btn btn-xs btn-ghost bg-base-100/90 shadow-sm"
											>
												{coverImageId === image.id
													? ($t('collection.cover') ?? 'Cover')
													: ($t('collection.set_cover') ?? 'Set cover')}
											</div>
										</button>
									{/each}
								</div>
								<div class="flex justify-end">
									<button
										type="button"
										class="btn btn-ghost btn-sm"
										onclick={() => selectCover(null)}
									>
										<CloseIcon class="w-4 h-4" />
										<span>{$t('collection.clear_cover') ?? 'Clear cover'}</span>
									</button>
								</div>
							{/if}
						</div>
					</div>
				{/if}

				<!-- Share Link Section (only if public and has ID) -->
				{#if collection.is_public && collection.id}
					<div class="card bg-base-100 border border-base-300 shadow-lg">
						<div class="card-body p-6">
							<h3 class="font-semibold text-lg mb-3">{$t('adventures.share_collection')}</h3>
							<div class="flex items-center gap-3">
								<input
									type="text"
									value="{window.location.origin}/collections/{collection.id}"
									readonly
									class="input flex-1 font-mono text-sm"
								/>
								<button
									type="button"
									onclick={async () => {
										try {
											await copyToClipboard(
												`${window.location.origin}/collections/${collection.id}`
											);
											addToast('success', $t('adventures.link_copied'));
										} catch {
											addToast('error', $t('adventures.copy_failed') || 'Copy failed');
										}
									}}
									class="btn btn-primary gap-2"
								>
									<LinkIcon class="w-4 h-4" />
									{$t('adventures.copy_link')}
								</button>
							</div>
						</div>
					</div>
				{/if}

				<!-- Action Buttons -->
				<div class="flex gap-3 justify-end pt-4">
					<button type="button" class="btn btn-neutral gap-2" onclick={close}>
						<CloseIcon class="w-5 h-5" />
						{$t('about.close')}
					</button>
					<button type="submit" class="btn btn-primary gap-2">
						<SaveIcon class="w-5 h-5" />
						{$t('notes.save')}
					</button>
				</div>
			</form>
		</div>
	</div>
</dialog>
