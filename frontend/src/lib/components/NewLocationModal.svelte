<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import type { Collection, Location, User } from '$lib/types';
	import { addToast } from '$lib/toasts';
	import { t } from 'svelte-i18n';
	import LocationQuickStart from './locations/LocationQuickStart.svelte';
	import LocationDetails from './locations/LocationDetails.svelte';
	import LocationMedia from './locations/LocationMedia.svelte';
	import LocationVisits from './locations/LocationVisits.svelte';

	export let user: User | null = null;
	export let collection: Collection | null = null;
	export let initialLatLng: { lat: number; lng: number } | null = null; // Used to pass the location from the map selection to the modal

	const dispatch = createEventDispatcher();

	let modal: HTMLDialogElement;

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

	export let location: Location = {
		id: '',
		name: '',
		visits: [],
		link: null,
		description: null,
		tags: [],
		rating: NaN,
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
		rating: locationToEdit?.rating || NaN,
		is_public: locationToEdit?.is_public || false,
		latitude: locationToEdit?.latitude || NaN,
		longitude: locationToEdit?.longitude || NaN,
		location: locationToEdit?.location || null,
		images: locationToEdit?.images || [],
		user: locationToEdit?.user || null,
		visits: locationToEdit?.visits || [],
		is_visited: locationToEdit?.is_visited || false,
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
	onMount(async () => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		modal.showModal();
		// Skip the quick start step if editing an existing location
		if (!locationToEdit) {
			steps[0].selected = true;
			steps[1].selected = false;
		} else {
			steps[0].selected = false;
			steps[1].selected = true;
		}
		if (initialLatLng) {
			location.latitude = initialLatLng.lat;
			location.longitude = initialLatLng.lng;
			steps[1].selected = true;
			steps[0].selected = false;
		}
	});

	function close() {
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
										d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5-5z"
										clip-rule="evenodd"
									/>
								</svg>
							</div>
							<button
								class="timeline-end timeline-box text-xs sm:text-sm px-2 py-1 sm:px-3 sm:py-2 {step.selected
									? 'bg-primary text-primary-content'
									: 'bg-base-200'} {step.requires_id && !location.id
									? 'opacity-50 cursor-not-allowed'
									: 'hover:bg-primary/80 cursor-pointer'} transition-colors"
								on:click={() => {
									// Reset all steps
									steps.forEach((s) => (s.selected = false));
									// Select clicked step
									steps[index].selected = true;
								}}
								disabled={step.requires_id && !location.id}
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
					<button class="btn btn-ghost btn-square" on:click={close}>
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
					<button class="btn btn-ghost btn-square" on:click={close}>
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

		{#if steps[0].selected}
			<!-- Main Content -->
			<LocationQuickStart
				on:locationSelected={(e) => {
					location.name = e.detail.name;
					location.location = e.detail.location;
					location.latitude = e.detail.latitude;
					location.longitude = e.detail.longitude;
					steps[0].selected = false;
					steps[1].selected = true;
				}}
				on:cancel={() => close()}
				on:next={() => {
					steps[0].selected = false;
					steps[1].selected = true;
				}}
			/>
		{/if}
		{#if steps[1].selected}
			<LocationDetails
				currentUser={user}
				initialLocation={location}
				{collection}
				bind:editingLocation={location}
				on:back={() => {
					steps[1].selected = false;
					steps[0].selected = true;
				}}
				on:save={(e) => {
					location.name = e.detail.name;
					location.category = e.detail.category;
					location.rating = e.detail.rating;
					location.is_public = e.detail.is_public;
					location.link = e.detail.link;
					location.description = e.detail.description;
					location.latitude = e.detail.latitude;
					location.longitude = e.detail.longitude;
					location.location = e.detail.location;
					location.tags = e.detail.tags;
					location.user = e.detail.user;
					location.id = e.detail.id;

					steps[1].selected = false;
					steps[2].selected = true;
				}}
			/>
		{/if}
		{#if steps[2].selected}
			<LocationMedia
				bind:images={location.images}
				bind:attachments={location.attachments}
				bind:trails={location.trails}
				itemName={location.name}
				userIsOwner={user?.uuid === location.user?.uuid}
				on:back={() => {
					steps[2].selected = false;
					steps[1].selected = true;
				}}
				itemId={location.id}
				on:next={() => {
					steps[2].selected = false;
					steps[3].selected = true;
				}}
				measurementSystem={user?.measurement_system || 'metric'}
			/>
		{/if}
		{#if steps[3].selected}
			<LocationVisits
				bind:visits={location.visits}
				bind:trails={location.trails}
				objectId={location.id}
				on:back={() => {
					steps[3].selected = false;
					steps[2].selected = true;
				}}
				on:close={() => close()}
				measurementSystem={user?.measurement_system || 'metric'}
				{collection}
			/>
		{/if}
	</div>
</dialog>
