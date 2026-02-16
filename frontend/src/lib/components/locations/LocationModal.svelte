<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import type { Collection, Location, User } from '$lib/types';
	import { t } from 'svelte-i18n';
	import LocationQuickStart from './LocationQuickStart.svelte';
	import LocationDetails from './LocationDetails.svelte';
	import LocationMedia from './LocationMedia.svelte';
	import LocationVisits from './LocationVisits.svelte';
	import { EntityModal, type ModalStep, navigateToStep } from '../shared/modal';
	import MapMarkerIcon from '~icons/mdi/map-marker';

	export let user: User | null = null;
	export let collection: Collection | null = null;
	export let initialLatLng: { lat: number; lng: number } | null = null;
	export let initialVisitDate: string | null = null;
	export let collaborativeMode: boolean = false;

	const dispatch = createEventDispatcher();

	// Store the initial visit date internally so it persists even if parent clears it
	let storedInitialVisitDate: string | null = initialVisitDate;

	// Whether a save/create occurred during this modal session
	let didSave = false;

	let entityModal: EntityModal;

	let steps: ModalStep[] = [
		{ name: $t('adventures.quick_start'), selected: true, requires_id: false },
		{ name: $t('adventures.details'), selected: false, requires_id: false },
		{ name: $t('adventures.visits'), selected: false, requires_id: true },
		{ name: $t('settings.media'), selected: false, requires_id: true }
	];

	export let location: Location = {
		id: '',
		name: '',
		visits: [],
		link: null,
		description: null,
		tags: [],
		price: null,
		price_currency: null,
		is_public: true,
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
		price: locationToEdit?.price ?? null,
		price_currency: locationToEdit?.price_currency ?? null,
		is_public: locationToEdit?.is_public ?? true,
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

	onMount(() => {
		// Skip the quick start step if editing an existing location
		if (!locationToEdit) {
			steps = navigateToStep(steps, 0);
		} else {
			steps = navigateToStep(steps, 1);
		}
		if (initialLatLng) {
			location.latitude = initialLatLng.lat;
			location.longitude = initialLatLng.lng;
			steps = navigateToStep(steps, 1);
		}
	});

	function close() {
		if (didSave) {
			dispatch(locationToEdit ? 'save' : 'create', location);
		}
		dispatch('close');
	}

	function handleStepsChange(e: CustomEvent<ModalStep[]>) {
		steps = e.detail;
	}

	$: modalTitle = locationToEdit ? $t('adventures.edit_location') : $t('adventures.new_location');
	$: modalSubtitle = locationToEdit
		? $t('adventures.update_location_details')
		: $t('adventures.create_new_location');
</script>

<EntityModal
	bind:this={entityModal}
	modalId="location_modal"
	icon={MapMarkerIcon}
	title={modalTitle}
	subtitle={modalSubtitle}
	{steps}
	entityId={location.id}
	{didSave}
	isEditing={!!locationToEdit}
	on:close={close}
	on:save={() => dispatch('save', location)}
	on:create={() => dispatch('create', location)}
	on:stepsChange={handleStepsChange}
>
	{#if steps[0].selected}
		<LocationQuickStart
			on:locationSelected={(e) => {
				location.name = e.detail.name;
				location.location = e.detail.location;
				location.latitude = e.detail.latitude;
				location.longitude = e.detail.longitude;
				steps = navigateToStep(steps, 1);
			}}
			on:cancel={close}
			on:next={() => {
				steps = navigateToStep(steps, 1);
			}}
		/>
	{/if}
	{#if steps[1].selected}
		{#key `${location.latitude}-${location.longitude}-${location.name}`}
		<LocationDetails
			currentUser={user}
			initialLocation={location}
			{collection}
			bind:editingLocation={location}
			on:back={() => {
				steps = navigateToStep(steps, 0);
			}}
			on:save={(e) => {
				location.name = e.detail.name;
				location.category = e.detail.category;
				location.is_public = e.detail.is_public;
				location.link = e.detail.link;
				location.description = e.detail.description;
				location.latitude = e.detail.latitude;
				location.longitude = e.detail.longitude;
				location.location = e.detail.location;
				location.tags = e.detail.tags;
				location.user = e.detail.user;
				location.id = e.detail.id;
				location.price = e.detail.price;
				location.price_currency = e.detail.price_currency;

				didSave = true;
				steps = navigateToStep(steps, 2);
			}}
		/>
		{/key}
	{/if}
	{#if steps[2].selected}
		<LocationVisits
			bind:visits={location.visits}
			bind:trails={location.trails}
			objectId={location.id}
			on:back={() => {
				steps = navigateToStep(steps, 1);
			}}
			on:close={() => {
				steps = navigateToStep(steps, 3);
			}}
			measurementSystem={user?.measurement_system || 'metric'}
			{collection}
			initialVisitDate={storedInitialVisitDate}
			currentUserUsername={user?.username || null}
			countryCurrency={location.country?.currency_code || null}
			userCurrency={user?.default_currency || null}
		/>
	{/if}
	{#if steps[3].selected}
		<LocationMedia
			bind:images={location.images}
			bind:attachments={location.attachments}
			bind:trails={location.trails}
			itemName={location.name}
			userIsOwner={user?.uuid === location.user?.uuid}
			on:back={() => {
				steps = navigateToStep(steps, 2);
			}}
			itemId={location.id}
			on:next={close}
			measurementSystem={user?.measurement_system || 'metric'}
			{collaborativeMode}
		/>
	{/if}
</EntityModal>
