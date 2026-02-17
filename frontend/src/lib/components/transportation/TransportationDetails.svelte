<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import type { Collection, Transportation, User } from '$lib/types';
	import LocationSearchMap from '../shared/LocationSearchMap.svelte';
	import { EntityDetailsBase } from '../shared/modal';
	import { TRANSPORTATION_TYPES_ICONS } from '$lib';
	import type { SearchMode } from '../shared/LocationSearchMap.svelte';
	import { transportationTypes, fetchEntityTypes } from '$lib/stores/entityTypes';

	const dispatch = createEventDispatcher();

	let isReverseGeocoding = false;
	export let searchMode: SearchMode = 'location';
	let previousTransportationType: string | null = null;

	// Props
	export let initialTransportation: any = null;
	export let currentUser: any = null;
	export let editingTransportation: any = null;
	export let collection: Collection | null = null;

	// Form data
	let transportation: any = {
		name: '',
		type: '',
		description: '',
		link: '',
		flight_number: null,
		from_location: null,
		to_location: null,
		origin_latitude: null,
		origin_longitude: null,
		destination_latitude: null,
		destination_longitude: null,
		start_code: null,
		end_code: null,
		distance: null,
		collections: collection?.id ? [collection.id] : [],
		is_public: true,
		tags: []
	};

	let startCodeField: string = '';
	let endCodeField: string = '';

	let user: User | null = null;
	let transportationToEdit: Transportation | null = null;

	$: user = currentUser;
	$: transportationToEdit = editingTransportation;

	function normalizeCode(code: string | null): string | null {
		if (!code) return null;
		const trimmed = code.trim().toUpperCase();
		if (!trimmed) return null;
		return trimmed.slice(0, 5);
	}

	function clearAirportCodes() {
		startCodeField = '';
		endCodeField = '';
		transportation.start_code = null;
		transportation.end_code = null;
	}

	function handleStartCodeEvent(event: Event) {
		const target = event.target as HTMLInputElement;
		startCodeField = target?.value || '';
		transportation.start_code = normalizeCode(startCodeField);
	}

	function handleEndCodeEvent(event: Event) {
		const target = event.target as HTMLInputElement;
		endCodeField = target?.value || '';
		transportation.end_code = normalizeCode(endCodeField);
	}

	// Track search mode changes
	let prevSearchMode = searchMode;
	$: if (prevSearchMode !== searchMode) {
		prevSearchMode = searchMode;
		if (searchMode === 'location') clearAirportCodes();
	}

	// Auto-set search mode based on transportation type
	$: if (transportation.type && previousTransportationType !== transportation.type) {
		previousTransportationType = transportation.type;
		// Only change searchMode if current mode is 'location' (default)
		// This allows the map to show appropriate search options for the type
		if (searchMode === 'location') {
			if (transportation.type === 'plane') {
				searchMode = 'airport';
			} else if (transportation.type === 'train') {
				searchMode = 'train';
			} else if (transportation.type === 'bus') {
				searchMode = 'bus';
			} else if (transportation.type === 'cab') {
				searchMode = 'cab';
			} else if (transportation.type === 'vtc') {
				searchMode = 'vtc';
			}
			// For car, boat, bike, walking, other - keep searchMode as 'location'
		}
	}

	function handleTransportationUpdate(
		event: CustomEvent<{
			start: { name: string; lat: number; lng: number; location: string; code?: string | null } | null;
			end: { name: string; lat: number; lng: number; location: string; code?: string | null } | null;
		}>
	) {
		const { start, end } = event.detail;

		if (start) {
			transportation.from_location = start.name;
			transportation.origin_latitude = start.lat;
			transportation.origin_longitude = start.lng;
			transportation.start_code = normalizeCode(start.code || '');
			startCodeField = startCodeField || transportation.start_code || '';
		}

		if (end) {
			transportation.to_location = end.name;
			transportation.destination_latitude = end.lat;
			transportation.destination_longitude = end.lng;
			transportation.end_code = normalizeCode(end.code || '');
			endCodeField = endCodeField || transportation.end_code || '';
		}

		if (!transportation.name && start && end) {
			transportation.name = `${start.name} → ${end.name}`;
		}
	}

	function handleLocationClear() {
		transportation.from_location = null;
		transportation.to_location = null;
		transportation.origin_latitude = null;
		transportation.origin_longitude = null;
		transportation.destination_latitude = null;
		transportation.destination_longitude = null;
		transportation.start_code = null;
		transportation.end_code = null;
	}

	async function handleSave() {
		if (!transportation.name || !transportation.type) return;

		transportation.start_code = normalizeCode(startCodeField || transportation.start_code);
		transportation.end_code = normalizeCode(endCodeField || transportation.end_code);

		// Round coordinates
		['origin_latitude', 'origin_longitude', 'destination_latitude', 'destination_longitude'].forEach(field => {
			if (transportation[field] !== null && typeof transportation[field] === 'number') {
				transportation[field] = parseFloat(transportation[field].toFixed(6));
			}
		});

		if (collection && collection.id) {
			if (!transportation.collections || transportation.collections.length === 0) {
				transportation.collections = [collection.id];
			} else if (!transportation.collections.includes(collection.id)) {
				transportation.collections = [...transportation.collections, collection.id];
			}
		}

		let payload: any = { ...transportation };

		if (!payload.link || payload.link.trim() === '') {
			delete payload.link;
		}

		if (transportationToEdit && transportationToEdit.id) {
			if (
				(!payload.collections || payload.collections.length === 0) &&
				transportationToEdit.collections &&
				transportationToEdit.collections.length > 0
			) {
				delete payload.collections;
			}

			const res = await fetch(`/api/transportations/${transportationToEdit.id}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload)
			});
			transportation = await res.json();
		} else {
			const res = await fetch(`/api/transportations`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload)
			});
			transportation = await res.json();
		}

		dispatch('save', { ...transportation });
	}

	function handleBack() {
		dispatch('back');
	}

	onMount(() => {
		// Fetch entity types from API
		fetchEntityTypes();

		if (initialTransportation && typeof initialTransportation === 'object') {
			transportation.name = initialTransportation.name || '';
			transportation.type = initialTransportation.type || '';
			transportation.link = initialTransportation.link || '';
			transportation.description = initialTransportation.description || '';
			transportation.is_public = initialTransportation.is_public ?? true;
			transportation.flight_number = initialTransportation.flight_number || null;
			transportation.start_code = initialTransportation.start_code || null;
			transportation.end_code = initialTransportation.end_code || null;
			transportation.distance = initialTransportation.distance || null;

			transportation.from_location = initialTransportation.from_location || null;
			transportation.to_location = initialTransportation.to_location || null;
			transportation.origin_latitude = initialTransportation.origin_latitude || null;
			transportation.origin_longitude = initialTransportation.origin_longitude || null;
			transportation.destination_latitude = initialTransportation.destination_latitude || null;
			transportation.destination_longitude = initialTransportation.destination_longitude || null;
			startCodeField = transportation.start_code || '';
			endCodeField = transportation.end_code || '';

			if (initialTransportation.tags && Array.isArray(initialTransportation.tags)) {
				transportation.tags = initialTransportation.tags;
			}
		}
	});
</script>

<EntityDetailsBase
	bind:name={transportation.name}
	bind:description={transportation.description}
	bind:link={transportation.link}
	bind:is_public={transportation.is_public}
	bind:tags={transportation.tags}
	namePlaceholder={$t('transportation.enter_transportation_name')}
	linkPlaceholder={$t('transportation.enter_link')}
	publicLabel={$t('transportation.public_transportation')}
	publicDescription={$t('transportation.public_transportation_description')}
	entityNameForGenerate={transportation.name}
	descriptionDisabled={!transportation.type}
	isProcessing={isReverseGeocoding}
	disabled={!transportation.name || !transportation.type || isReverseGeocoding}
	on:save={handleSave}
	on:back={handleBack}
>
	<svelte:fragment slot="type-field">
		<!-- Type Field -->
		<div class="form-control">
			<label class="label" for="type">
				<span class="label-text font-medium">
					{$t('transportation.type')} <span class="text-error">*</span>
				</span>
			</label>
			<select
				class="select select-bordered w-full bg-base-100/80 focus:bg-base-100"
				name="type"
				id="type"
				required
				bind:value={transportation.type}
			>
				<option disabled value="">{$t('transportation.select_type')}</option>
				{#if $transportationTypes.length > 0}
					{#each $transportationTypes as type}
						<option value={type.key}>{type.icon} {type.name}</option>
					{/each}
				{:else}
					{#each Object.entries(TRANSPORTATION_TYPES_ICONS) as [key, icon]}
						<option value={key}>{icon} {key.charAt(0).toUpperCase() + key.slice(1)}</option>
					{/each}
				{/if}
			</select>
		</div>
	</svelte:fragment>

	<svelte:fragment slot="left-extra">
		<!-- Transport ID (Flight number, train number, etc.) -->
		<div class="form-control">
			<label class="label" for="flight_number">
				<span class="label-text font-medium">{$t('transportation.transport_id')}</span>
			</label>
			<input
				type="text"
				id="flight_number"
				bind:value={transportation.flight_number}
				class="input input-bordered bg-base-100/80 focus:bg-base-100"
				placeholder={$t('transportation.enter_transport_id')}
			/>
		</div>

		<!-- Start/End Codes -->
		{#if searchMode !== 'location'}
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
				<div class="form-control">
					<label class="label" for="start_code">
						<span class="label-text font-medium">
							{$t('transportation.departure_code') || 'Departure code'}
						</span>
					</label>
					<input
						type="text"
						id="start_code"
						value={startCodeField}
						on:input={handleStartCodeEvent}
						class="input input-bordered bg-base-100/80 focus:bg-base-100 uppercase"
						maxlength="5"
						placeholder={searchMode === 'airport' ? 'JFK' : $t('transportation.departure_code')}
					/>
				</div>
				<div class="form-control">
					<label class="label" for="end_code">
						<span class="label-text font-medium">
							{$t('transportation.arrival_code') || 'Arrival code'}
						</span>
					</label>
					<input
						type="text"
						id="end_code"
						value={endCodeField}
						on:input={handleEndCodeEvent}
						class="input input-bordered bg-base-100/80 focus:bg-base-100 uppercase"
						maxlength="5"
						placeholder={searchMode === 'airport' ? 'LHR' : $t('transportation.arrival_code')}
					/>
				</div>
			</div>
		{/if}
	</svelte:fragment>

	<svelte:fragment slot="map">
		<LocationSearchMap
			bind:isReverseGeocoding
			transportationMode={true}
			unifiedSearch={true}
			bind:searchMode
			showDisplayNameInput={false}
			initialStartLocation={initialTransportation?.origin_latitude && initialTransportation?.origin_longitude
				? {
						name: initialTransportation.from_location || '',
						lat: Number(initialTransportation.origin_latitude),
						lng: Number(initialTransportation.origin_longitude),
						location: initialTransportation.from_location || ''
					}
				: null}
			initialEndLocation={initialTransportation?.destination_latitude && initialTransportation?.destination_longitude
				? {
						name: initialTransportation.to_location || '',
						lat: Number(initialTransportation.destination_latitude),
						lng: Number(initialTransportation.destination_longitude),
						location: initialTransportation.to_location || ''
					}
				: null}
			initialStartCode={initialTransportation?.start_code || null}
			initialEndCode={initialTransportation?.end_code || null}
			on:transportationUpdate={handleTransportationUpdate}
			on:clear={handleLocationClear}
		/>
	</svelte:fragment>
</EntityDetailsBase>
