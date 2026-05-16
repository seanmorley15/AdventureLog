<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import type { Collection, Location, User } from '$lib/types';
	import { addToast } from '$lib/toasts';
	import { t } from 'svelte-i18n';
	import { normalizeBasemapType } from '$lib';
	import LocationQuickStart from './LocationQuickStart.svelte';
	import LocationDetails from './LocationDetails.svelte';
	import LocationMedia from './LocationMedia.svelte';
	import LocationVisits from './LocationVisits.svelte';

	export let user: User | null = null;
	export let collection: Collection | null = null;
	export let initialLatLng: { lat: number; lng: number } | null = null; // Used to pass the location from the map selection to the modal
	export let initialVisitDate: string | null = null; // Used to pre-fill visit date when adding from itinerary planner
	export let itineraryDayLabel: string | null = null;

	const dispatch = createEventDispatcher();

	// Store the initial visit date internally so it persists even if parent clears it
	let storedInitialVisitDate: string | null = initialVisitDate;

	let modal: HTMLDialogElement;
	let googleMapsEnabled = false;
	let isEditMode = false;
	let pendingGooglePhotoUrls: string[] = [];
	let importingGooglePhotos = false;

	// Whether a save/create occurred during this modal session
	let didSave = false;

	let steps = [
		{
			name: $t('adventures.quick_start'),
			selected: true,
			requires_id: false
		},
		{
			name: $t('adventures.details'),
			selected: false,
			requires_id: false
		},
		{
			name: $t('settings.media'),
			selected: false,
			requires_id: true
		},
		{
			name: $t('adventures.visits'),
			selected: false,
			requires_id: true
		}
	];

	function setStep(stepIndex: number) {
		steps = steps.map((step, index) => ({
			...step,
			selected: index === stepIndex
		}));
	}

	function handleStepSelect(stepIndex: number) {
		if (stepIndex === 0 && isEditMode) {
			return;
		}
		if (steps[stepIndex]?.requires_id && !location.id) {
			return;
		}
		setStep(stepIndex);
	}

	function handleDetailsBack() {
		if (isEditMode) {
			close();
			return;
		}
		setStep(0);
	}

	function applyQuickStartPrefill(prefill: any) {
		if (!prefill) return;

		if (prefill.name) location.name = prefill.name;
		if (prefill.location) location.location = prefill.location;
		if (typeof prefill.latitude === 'number') location.latitude = prefill.latitude;
		if (typeof prefill.longitude === 'number') location.longitude = prefill.longitude;
		if (typeof prefill.rating === 'number') location.rating = prefill.rating;
		if (!location.link && (prefill.website || prefill.google_maps_url)) {
			location.link = prefill.website || prefill.google_maps_url;
		}
		if (!location.description && prefill.description) {
			location.description = prefill.description;
		}
		if ((!location.tags || location.tags.length === 0) && Array.isArray(prefill.types)) {
			location.tags = prefill.types.slice(0, 8);
		}
		if (prefill.selected_category && typeof prefill.selected_category === 'object') {
			location.category = prefill.selected_category;
		}
		pendingGooglePhotoUrls = Array.isArray(prefill.photos)
			? prefill.photos.filter((url: unknown) => typeof url === 'string' && url.trim()).slice(0, 5)
			: [];
	}

	async function importPendingGoogleImages(locationId: string) {
		if (!locationId || pendingGooglePhotoUrls.length === 0) return;
		importingGooglePhotos = true;

		try {
			const res = await fetch('/api/images/import_from_urls/', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					content_type: 'location',
					object_id: locationId,
					urls: pendingGooglePhotoUrls
				})
			});

			if (!res.ok) {
				addToast('warning', 'Location saved, but Google photos could not be imported');
				return;
			}

			const data = await res.json();
			if (Array.isArray(data.created) && data.created.length > 0) {
				const existingImages = Array.isArray(location.images) ? location.images : [];
				const existingIds = new Set(existingImages.map((img: any) => img.id));
				const imported = data.created.filter((img: any) => !existingIds.has(img.id));
				location.images = [...existingImages, ...imported];
			}

			pendingGooglePhotoUrls = [];
		} catch {
			addToast('warning', 'Location saved, but Google photos import failed');
		} finally {
			importingGooglePhotos = false;
		}
	}

	async function loadIntegrations() {
		try {
			const res = await fetch('/api/integrations/');
			if (!res.ok) return;
			const integrations = await res.json();
			googleMapsEnabled = Boolean(integrations?.google_maps);
		} catch {
			googleMapsEnabled = false;
		}
	}

	export let location: Location = {
		id: '',
		name: '',
		visits: [],
		link: null,
		description: null,
		tags: [],
		rating: NaN,
		price: null,
		price_currency: null,
		is_public: false,
		latitude: NaN,
		longitude: NaN,
		location: null,
		images: [],
		user: null,
		category: {
			id: '',
			name: '',
			display_name: '',
			icon: '',
			user: ''
		},
		attachments: [],
		trails: []
	};

	export let locationToEdit: Location | null = null;

	location = {
		id: locationToEdit?.id || '',
		name: locationToEdit?.name || '',
		link: locationToEdit?.link || null,
		description: locationToEdit?.description || null,
		tags: locationToEdit?.tags || [],
		rating: locationToEdit?.rating ?? NaN,
		price: locationToEdit?.price ?? null,
		price_currency: locationToEdit?.price_currency ?? null,
		is_public: locationToEdit?.is_public ?? false,
		latitude: locationToEdit?.latitude ?? NaN,
		longitude: locationToEdit?.longitude ?? NaN,
		location: locationToEdit?.location || null,
		images: locationToEdit?.images || [],
		user: locationToEdit?.user || null,
		visits: locationToEdit?.visits || [],
		is_visited: locationToEdit?.is_visited ?? false,
		collections: locationToEdit?.collections || [],
		category: locationToEdit?.category || {
			id: '',
			name: '',
			display_name: '',
			icon: '',
			user: ''
		},
		trails: locationToEdit?.trails || [],
		attachments: locationToEdit?.attachments || []
	};

	onMount(() => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		modal.showModal();
		isEditMode = Boolean(locationToEdit?.id);

		// Skip the quick start step if editing an existing location
		if (!isEditMode) {
			setStep(0);
		} else {
			setStep(1);
		}

		if (initialLatLng) {
			location.latitude = initialLatLng.lat;
			location.longitude = initialLatLng.lng;
			setStep(1);
		}

		void loadIntegrations();
	});

	function close() {
		// If a save occurred, notify the parent with appropriate event
		if (didSave) {
			if (locationToEdit) {
				dispatch('save', location);
			} else {
				dispatch('create', location);
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
						<svg class="w-8 h-8 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
							/>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
							/>
						</svg>
					</div>
					<div>
						<h1 class="text-3xl font-bold text-primary bg-clip-text">
							{locationToEdit ? $t('adventures.edit_location') : $t('adventures.new_location')}
						</h1>
						<p class="text-sm text-base-content/60">
							{locationToEdit
								? $t('adventures.update_location_details')
								: $t('adventures.create_new_location')}
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
										d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
										clip-rule="evenodd"
									/>
								</svg>
							</div>
							<button
								class="timeline-end timeline-box text-xs sm:text-sm px-2 py-1 sm:px-3 sm:py-2 {step.selected
									? 'bg-primary text-primary-content'
									: 'bg-base-200'} {step.requires_id && !location.id
									? 'opacity-50 cursor-not-allowed'
									: ''} {index === 0 && isEditMode
									? 'opacity-50 cursor-not-allowed'
									: 'hover:bg-primary/80 cursor-pointer'} transition-colors"
								on:click={() => handleStepSelect(index)}
								disabled={(step.requires_id && !location.id) || (index === 0 && isEditMode)}
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
				{#if !location.id}
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
				{:else}
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
				{/if}
			</div>
		</div>

		{#if steps[0].selected && !isEditMode}
			<!-- Main Content -->
			<LocationQuickStart
				googleEnabled={googleMapsEnabled}
				collectionId={collection?.id || null}
				itineraryDate={storedInitialVisitDate}
				itineraryLabel={itineraryDayLabel}
				basemapType={normalizeBasemapType(user?.map_style)}
				on:addDetails={(e) => {
					applyQuickStartPrefill(e.detail.prefill);
					setStep(1);
				}}
				on:manual={() => {
					setStep(1);
				}}
				on:quickAdded={(e) => {
					location = e.detail.location;
					pendingGooglePhotoUrls = [];
					didSave = true;
					dispatch('quickAddCreated', {
						location: e.detail.location,
						itineraryItem: e.detail.itineraryItem || null,
						itineraryDate: e.detail.itineraryDate || null
					});
					close();
				}}
				on:quickAddedEdit={(e) => {
					location = e.detail.location;
					pendingGooglePhotoUrls = [];
					didSave = true;
					setStep(1);
				}}
				on:quickAddedDone={(e) => {
					location = e.detail.location;
					pendingGooglePhotoUrls = [];
					didSave = true;
					close();
				}}
				on:cancel={() => close()}
			/>
		{/if}
		{#if steps[1].selected}
			<LocationDetails
				currentUser={user}
				initialLocation={location}
				{collection}
				bind:editingLocation={location}
				on:back={handleDetailsBack}
				on:save={async (e) => {
					location = {
						...location,
						...e.detail,
						tags: e.detail.tags || location.tags || [],
						images: e.detail.images || location.images || [],
						attachments: e.detail.attachments || location.attachments || [],
						trails: e.detail.trails || location.trails || [],
						visits: e.detail.visits || location.visits || []
					};

					// Mark that a save occurred so close() will notify parent
					didSave = true;

					if (location.id) {
						setStep(2);
						if (pendingGooglePhotoUrls.length > 0) {
							void importPendingGoogleImages(location.id);
						}
					} else {
						// Stay on details if save failed (no ID returned)
						setStep(1);
					}
				}}
			/>
		{/if}
		{#if steps[2].selected}
			{#if importingGooglePhotos}
				<div class="alert alert-info mb-4">
					<span class="loading loading-spinner loading-sm"></span>
					<span>Importing Google photos in the background. They will appear here shortly.</span>
				</div>
			{/if}
			<LocationMedia
				bind:images={location.images}
				bind:attachments={location.attachments}
				bind:trails={location.trails}
				itemName={location.name}
				userIsOwner={user?.uuid === location.user?.uuid}
				on:back={() => setStep(1)}
				itemId={location.id}
				on:next={() => setStep(3)}
				measurementSystem={user?.measurement_system || 'metric'}
			/>
		{/if}
		{#if steps[3].selected}
			<LocationVisits
				bind:visits={location.visits}
				bind:trails={location.trails}
				objectId={location.id}
				on:back={() => setStep(2)}
				on:close={() => close()}
				measurementSystem={user?.measurement_system || 'metric'}
				{collection}
				initialVisitDate={storedInitialVisitDate}
			/>
		{/if}
	</div>
</dialog>
