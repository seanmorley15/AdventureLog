<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import type { Collection, Lodging, User } from '$lib/types';
	import { addToast } from '$lib/toasts';
	import { t } from 'svelte-i18n';
	import Bed from '~icons/mdi/bed';
	import LodgingQuickStart from './LodgingQuickStart.svelte';
	import LodgingDetails from './LodgingDetails.svelte';
	import MediaStep from '../shared/MediaStep.svelte';
	import LodgingVisits from './LodgingVisits.svelte';
	import { EntityModal, type ModalStep, navigateToStep } from '../shared/modal';

	export let user: User | null = null;
	export let collection: Collection | null = null;
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

	function createEmptyLodging(): Lodging {
		return {
			id: '',
			user: '',
			name: '',
			type: '',
			description: null,
			rating: null,
			link: null,
			reservation_number: null,
			price: null,
			price_currency: 'USD',
			latitude: null,
			longitude: null,
			location: null,
			is_public: true,
			collections: [],
			created_at: '',
			updated_at: '',
			images: [],
			attachments: [],
			visits: [],
			tags: null
		};
	}

	export let lodging: Lodging = createEmptyLodging();
	export let lodgingToEdit: Lodging | null = null;

	// Track which lodging we're currently editing to prevent unnecessary overwrites
	let previousLodgingId: string | null = null;

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
					reservation_number: lodgingToEdit.reservation_number || null,
					price: lodgingToEdit.price || null,
					price_currency: lodgingToEdit.price_currency || 'USD',
					latitude: lodgingToEdit.latitude || null,
					longitude: lodgingToEdit.longitude || null,
					location: lodgingToEdit.location || null,
					is_public: lodgingToEdit.is_public ?? true,
					collections: lodgingToEdit.collections || [],
					created_at: lodgingToEdit.created_at || '',
					updated_at: lodgingToEdit.updated_at || '',
					images: lodgingToEdit.images || [],
					attachments: lodgingToEdit.attachments || [],
					visits: lodgingToEdit.visits || [],
					tags: lodgingToEdit.tags || null
				};
				// When editing, skip quick start and go to details
				steps = navigateToStep(steps, 1);
			} else if (!lodging?.id) {
				lodging = createEmptyLodging();
				storedInitialVisitDate = initialVisitDate;
				steps = navigateToStep(steps, 0);
			}
		}
	}

	function close() {
		if (didSave) {
			dispatch(lodgingToEdit ? 'save' : 'create', lodging);
		}
		dispatch('close');
	}

	function handleStepsChange(e: CustomEvent<ModalStep[]>) {
		steps = e.detail;
	}

	$: modalTitle = lodgingToEdit ? $t('lodging.edit_lodging') : $t('lodging.new_lodging');
	$: modalSubtitle = lodgingToEdit
		? $t('lodging.update_lodging_details')
		: $t('lodging.create_new_lodging');
</script>

<EntityModal
	bind:this={entityModal}
	modalId="lodging_modal"
	icon={Bed}
	title={modalTitle}
	subtitle={modalSubtitle}
	{steps}
	entityId={lodging?.id ?? ''}
	{didSave}
	isEditing={!!lodgingToEdit}
	on:close={close}
	on:save={() => dispatch('save', lodging)}
	on:create={() => dispatch('create', lodging)}
	on:stepsChange={handleStepsChange}
>
	{#if steps[0].selected}
		<LodgingQuickStart
			on:cancel={close}
			on:next={() => {
				steps = navigateToStep(steps, 1);
			}}
			on:locationSelected={(e) => {
				const { name, latitude, longitude, location } = e.detail;
				// Always update name when new location is selected
				if (name) lodging.name = name;
				lodging.latitude = latitude;
				lodging.longitude = longitude;
				lodging.location = location;
				steps = navigateToStep(steps, 1);
			}}
		/>
	{/if}
	{#if steps[1].selected}
		{#key `${lodging.latitude}-${lodging.longitude}-${lodging.name}`}
		<LodgingDetails
			currentUser={user}
			initialLodging={lodging}
			{collection}
			bind:editingLodging={lodging}
			on:back={() => {
				steps = navigateToStep(steps, 0);
			}}
			on:save={(e) => {
				const detail = e.detail || {};
				const previousImages = lodging.images || [];
				const previousAttachments = lodging.attachments || [];
				lodging = { ...lodging, ...detail };

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

				didSave = true;

				if (!lodging?.id) {
					addToast('error', $t('adventures.lodging_save_error'));
					steps = navigateToStep(steps, 1);
					return;
				}

				steps = navigateToStep(steps, 2);
			}}
		/>
		{/key}
	{/if}
	{#if steps[2].selected}
		<LodgingVisits
			{collection}
			visits={lodging.visits || []}
			lodgingId={lodging.id}
			initialVisitDate={storedInitialVisitDate}
			currentUserUsername={user?.username || null}
			countryCurrency={lodging.country?.currency_code || null}
			userCurrency={user?.default_currency || null}
			on:back={() => {
				steps = navigateToStep(steps, 1);
			}}
			on:close={() => {
				steps = navigateToStep(steps, 3);
			}}
			on:visitAdded={(e) => {
				const existingVisits = (lodging.visits || []).filter((v) => v.id !== e.detail.id);
				lodging.visits = [...existingVisits, e.detail];
			}}
			on:visitDeleted={(e) => {
				lodging.visits = (lodging.visits || []).filter((v) => v.id !== e.detail);
			}}
		/>
	{/if}
	{#if steps[3].selected}
		<MediaStep
			bind:images={lodging.images}
			bind:attachments={lodging.attachments}
			itemName={lodging.name}
			on:back={() => {
				steps = navigateToStep(steps, 2);
			}}
			on:close={close}
			itemId={lodging.id}
			contentType="lodging"
			{collaborativeMode}
		/>
	{/if}
</EntityModal>
