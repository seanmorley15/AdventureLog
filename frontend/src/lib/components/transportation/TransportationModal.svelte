<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import type { Collection, Location, Transportation, User } from '$lib/types';
	import { addToast } from '$lib/toasts';
	import { t } from 'svelte-i18n';
	import Plane from '~icons/mdi/airplane';
	import MediaStep from '../shared/MediaStep.svelte';
	import TransportationDetails from './TransportationDetails.svelte';

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

	function createEmptyTransportation(): Transportation {
		return {
			id: '',
			user: '',
			name: '',
			type: '',
			description: null,
			rating: null,
			link: null,
			date: null,
			end_date: null,
			start_timezone: null,
			end_timezone: null,
			flight_number: null,
			from_location: null,
			to_location: null,
			origin_latitude: null,
			origin_longitude: null,
			destination_latitude: null,
			destination_longitude: null,
			start_code: null,
			end_code: null,
			is_public: false,
			distance: null,
			price: null,
			price_currency: 'USD',
			collection: null,
			created_at: '',
			updated_at: '',
			images: [],
			attachments: []
		};
	}

	export let transportation: Transportation = createEmptyTransportation();

	export let transportationToEdit: Transportation | null = null;

	// Track which transportation we're currently editing to prevent unnecessary overwrites
	let previousTransportationId: string | null = null;

	// Reactively update internal state when switching between edit/new.
	// This prevents stale values when the parent reuses `bind:transportation`.
	// Only runs when actually switching to a different transportation, not on every reactive update.
	$: {
		const currentTransportationId = transportationToEdit?.id || null;

		if (currentTransportationId !== previousTransportationId) {
			previousTransportationId = currentTransportationId;

			if (transportationToEdit) {
				transportation = {
					id: transportationToEdit.id || '',
					user: transportationToEdit.user || '',
					name: transportationToEdit.name || '',
					type: transportationToEdit.type || '',
					description: transportationToEdit.description || null,
					rating: transportationToEdit.rating || null,
					link: transportationToEdit.link || null,
					date: transportationToEdit.date || null,
					end_date: transportationToEdit.end_date || null,
					start_timezone: transportationToEdit.start_timezone || null,
					end_timezone: transportationToEdit.end_timezone || null,
					flight_number: transportationToEdit.flight_number || null,
					from_location: transportationToEdit.from_location || null,
					to_location: transportationToEdit.to_location || null,
					origin_latitude: transportationToEdit.origin_latitude || null,
					origin_longitude: transportationToEdit.origin_longitude || null,
					destination_latitude: transportationToEdit.destination_latitude || null,
					destination_longitude: transportationToEdit.destination_longitude || null,
					start_code: transportationToEdit.start_code || null,
					end_code: transportationToEdit.end_code || null,
					is_public: transportationToEdit.is_public || false,
					distance: transportationToEdit.distance || null,
					price: transportationToEdit.price ?? null,
					price_currency: transportationToEdit.price_currency || 'USD',
					collection: transportationToEdit.collection || null,
					created_at: transportationToEdit.created_at || '',
					updated_at: transportationToEdit.updated_at || '',
					images: transportationToEdit.images || [],
					attachments: transportationToEdit.attachments || []
				};
			} else if (!transportation?.id) {
				// Only reset to empty if we don't already have a saved transportation with an ID
				transportation = createEmptyTransportation();
				storedInitialVisitDate = initialVisitDate;
				// Reset steps to details when creating a new transportation
				steps = [
					{ name: $t('adventures.details'), selected: true, requires_id: false },
					{ name: $t('settings.media'), selected: false, requires_id: true }
				];
			}
		}
	}

	onMount(async () => {
		modal = document.getElementById('transportation_modal') as HTMLDialogElement;
		modal.showModal();
	});

	function close() {
		// If a save occurred, notify the parent with appropriate event
		if (didSave) {
			if (transportationToEdit) {
				dispatch('save', transportation);
			} else {
				dispatch('create', transportation);
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
<dialog id="transportation_modal" class="modal backdrop-blur-sm">
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
						<Plane class="w-6 h-6 text-primary" />
					</div>
					<div>
						<h1 class="text-3xl font-bold text-primary bg-clip-text">
							{transportationToEdit
								? $t('transportation.edit_transportation')
								: $t('transportation.new_transportation')}
						</h1>
						<p class="text-sm text-base-content/60">
							{transportationToEdit
								? $t('transportation.update_transportation_details')
								: $t('transportation.create_new_transportation')}
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
									: 'bg-base-200'} {step.requires_id && !transportation?.id
									? 'opacity-50 cursor-not-allowed'
									: 'hover:bg-primary/80 cursor-pointer'} transition-colors"
								on:click={() => {
									// Reset all steps
									steps.forEach((s) => (s.selected = false));
									// Select clicked step
									steps[index].selected = true;
								}}
								disabled={step.requires_id && !transportation?.id}
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
			<TransportationDetails
				currentUser={user}
				initialTransportation={transportation}
				{collection}
				bind:editingTransportation={transportation}
				on:back={() => {
					steps[1].selected = false;
					steps[0].selected = true;
				}}
				on:save={(e) => {
					// Update the entire transportation object with all saved data
					transportation = { ...transportation, ...e.detail };

					// Mark that a save occurred so close() will notify parent
					didSave = true;

					// Only allow moving to Media once we have a persisted id.
					if (!transportation?.id) {
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
				bind:images={transportation.images}
				bind:attachments={transportation.attachments}
				itemName={transportation.name}
				on:back={() => {
					steps[1].selected = false;
					steps[0].selected = true;
				}}
				on:close={() => close()}
				itemId={transportation.id}
				contentType="transportation"
				start_date={transportation.date}
				end_date={transportation.end_date}
				{user}
			/>
		{/if}
	</div>
</dialog>
