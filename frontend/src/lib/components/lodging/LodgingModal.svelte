<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import type { Collection, Lodging, User } from '$lib/types';
	import { addToast } from '$lib/toasts';
	import { t } from 'svelte-i18n';
	import Bed from '~icons/mdi/bed';
	import LodgingDetails from './LodgingDetails.svelte';
	import MediaStep from '../shared/MediaStep.svelte';

	export let user: User | null = null;
	export let collection: Collection | null = null;
	export let initialVisitDate: string | null = null; // Used to pre-fill visit date when adding from itinerary planner

	const dispatch = createEventDispatcher();

	// Store the initial visit date internally so it persists even if parent clears it
	let storedInitialVisitDate: string | null = initialVisitDate;

	let modal: HTMLDialogElement;

	// Whether a save/create occurred during this modal session
	let didSave = false;

	let steps = [
		{
			name: $t('adventures.details'),
			selected: true,
			requires_id: false
		},
		{
			name: $t('settings.media'),
			selected: false,
			requires_id: true
		}
	];

	function createEmptyLodging(): Lodging {
		return {
			id: '',
			user: '',
			name: '',
			type: '',
			description: null,
			rating: null,
			link: null,
			check_in: null,
			check_out: null,
			timezone: null,
			reservation_number: null,
			price: null,
			price_currency: 'USD',
			latitude: null,
			longitude: null,
			location: null,
			is_public: false,
			collection: null,
			created_at: '',
			updated_at: '',
			images: [],
			attachments: []
		};
	}

	export let lodging: Lodging = createEmptyLodging();

	export let lodgingToEdit: Lodging | null = null;

	// Track which lodging we're currently editing to prevent unnecessary overwrites
	let previousLodgingId: string | null = null;

	// Reactively update internal state when switching between edit/new.
	// This prevents stale values when the parent reuses `bind:lodging`.
	// Only runs when actually switching to a different lodging, not on every reactive update.
	$: {
		const currentLodgingId = lodgingToEdit?.id ?? null;

		if (currentLodgingId !== previousLodgingId) {
			previousLodgingId = currentLodgingId;

			if (lodgingToEdit) {
				lodging = {
					id: lodgingToEdit.id || '',
					user: lodgingToEdit.user || '',
					name: lodgingToEdit.name || '',
					type: lodgingToEdit.type || '',
					description: lodgingToEdit.description || null,
					rating: lodgingToEdit.rating || null,
					link: lodgingToEdit.link || null,
					check_in: lodgingToEdit.check_in || null,
					check_out: lodgingToEdit.check_out || null,
					timezone: lodgingToEdit.timezone || null,
					reservation_number: lodgingToEdit.reservation_number || null,
					price: lodgingToEdit.price || null,
					price_currency: lodgingToEdit.price_currency || 'USD',
					latitude: lodgingToEdit.latitude || null,
					longitude: lodgingToEdit.longitude || null,
					location: lodgingToEdit.location || null,
					is_public: lodgingToEdit.is_public || false,
					collection: lodgingToEdit.collection || null,
					created_at: lodgingToEdit.created_at || '',
					updated_at: lodgingToEdit.updated_at || '',
					images: lodgingToEdit.images || [],
					attachments: lodgingToEdit.attachments || []
				};
			} else if (!lodging?.id) {
				// Only reset to empty if we don't already have a saved lodging with an ID
				lodging = createEmptyLodging();
				storedInitialVisitDate = initialVisitDate;
				// Reset steps to details when creating a new lodging
				steps = [
					{ name: $t('adventures.details'), selected: true, requires_id: false },
					{ name: $t('settings.media'), selected: false, requires_id: true }
				];
			}
		}
	}

	onMount(async () => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		modal.showModal();
	});

	function close() {
		// If a save occurred, notify the parent with appropriate event
		if (didSave) {
			if (lodgingToEdit) {
				dispatch('save', lodging);
			} else {
				dispatch('create', lodging);
			}
		}

		dispatch('close');
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			close();
		}
	}
</script>

<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
<dialog id="my_modal_1" class="modal backdrop-blur-sm">
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div
		class="modal-box w-11/12 max-w-6xl bg-gradient-to-br from-base-100 via-base-100 to-base-200 border border-base-300 shadow-2xl"
		role="dialog"
		on:keydown={handleKeydown}
		tabindex="0"
	>
		<!-- Header Section - Following adventurelog pattern -->
		<div
			class="top-0 z-10 bg-base-100/90 backdrop-blur-lg border-b border-base-300 -mx-6 -mt-6 px-6 py-4 mb-6"
		>
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-3">
					<div class="p-2 bg-primary/10 rounded-xl">
						<Bed class="w-6 h-6 text-primary" />
					</div>
					<div>
						<h1 class="text-3xl font-bold text-primary bg-clip-text">
							{lodgingToEdit ? $t('lodging.edit_lodging') : $t('lodging.new_lodging')}
						</h1>
						<p class="text-sm text-base-content/60">
							{lodgingToEdit
								? $t('lodging.update_lodging_details')
								: $t('lodging.create_new_lodging')}
						</p>
					</div>
				</div>

				<ul
					class="timeline timeline-vertical timeline-compact sm:timeline-horizontal sm:timeline-normal"
				>
					{#each steps as step, index}
						<li>
							{#if index > 0}
								<hr class="bg-base-300" />
							{/if}
							<div class="timeline-middle">
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									class="h-4 w-4 sm:h-5 sm:w-5 {step.selected
										? 'text-primary'
										: 'text-base-content/40'}"
								>
									<path
										fill-rule="evenodd"
										d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-0.089l4-5-5z"
										clip-rule="evenodd"
									/>
								</svg>
							</div>
							<button
								class="timeline-end timeline-box text-xs sm:text-sm px-2 py-1 sm:px-3 sm:py-2 {step.selected
									? 'bg-primary text-primary-content'
									: 'bg-base-200'} {step.requires_id && !lodging?.id
									? 'opacity-50 cursor-not-allowed'
									: 'hover:bg-primary/80 cursor-pointer'} transition-colors"
								on:click={() => {
									// Reset all steps
									steps.forEach((s) => (s.selected = false));
									// Select clicked step
									steps[index].selected = true;
								}}
								disabled={step.requires_id && !lodging?.id}
							>
								<span class="hidden sm:inline">{step.name}</span>
								<span class="sm:hidden"
									>{step.name.substring(0, 8)}{step.name.length > 8 ? '...' : ''}</span
								>
							</button>
							{#if index < steps.length - 1}
								<hr class="bg-base-300" />
							{/if}
						</li>
					{/each}
				</ul>

				<!-- Close Button -->
				<button
					type="button"
					class="btn btn-ghost btn-square"
					aria-label={$t('about.close')}
					title={$t('about.close')}
					on:click={close}
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						/>
					</svg>
				</button>
			</div>
		</div>

		{#if steps[0].selected}
			<LodgingDetails
				currentUser={user}
				initialLodging={lodging}
				{collection}
				bind:editingLodging={lodging}
				on:back={() => {
					steps[1].selected = false;
					steps[0].selected = true;
				}}
				on:save={(e) => {
					// Update the entire lodging object with all saved data
					const detail = e.detail || {};
					const previousImages = lodging.images || [];
					const previousAttachments = lodging.attachments || [];
					lodging = { ...lodging, ...detail };
					// Preserve any prefilled 'rec-' images or attachments if the server returned an empty array
					if (Array.isArray(detail.images)) {
						if (
							detail.images.length === 0 &&
							previousImages.some((i) => String(i.id).startsWith('rec-'))
						) {
							lodging.images = previousImages;
						}
					} else {
						lodging.images = previousImages;
					}
					if (Array.isArray(detail.attachments)) {
						if (
							detail.attachments.length === 0 &&
							previousAttachments.some((a) => String(a.id).startsWith('rec-'))
						) {
							lodging.attachments = previousAttachments;
						}
					} else {
						lodging.attachments = previousAttachments;
					}

					// Mark that a save occurred so close() will notify parent
					didSave = true;

					// Only allow moving to Media once we have a persisted id.
					if (!lodging?.id) {
						addToast('error', $t('adventures.lodging_save_error'));
						steps[1].selected = false;
						steps[0].selected = true;
						return;
					}

					steps[0].selected = false;
					steps[1].selected = true;
				}}
				initialVisitDate={storedInitialVisitDate}
			/>
		{/if}
		{#if steps[1].selected}
			<MediaStep
				bind:images={lodging.images}
				bind:attachments={lodging.attachments}
				itemName={lodging.name}
				on:back={() => {
					steps[1].selected = false;
					steps[0].selected = true;
				}}
				on:close={() => close()}
				itemId={lodging.id}
				contentType="lodging"
			/>
		{/if}
	</div>
</dialog>
