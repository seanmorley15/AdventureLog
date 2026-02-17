<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import type { Collection, Lodging, User } from '$lib/types';
	import LocationSearchMap from '../shared/LocationSearchMap.svelte';
	import { EntityDetailsBase } from '../shared/modal';
	import { lodgingTypes, fetchEntityTypes } from '$lib/stores/entityTypes';

	const dispatch = createEventDispatcher();

	let isReverseGeocoding = false;

	let initialSelection: {
		name: string;
		lat: number;
		lng: number;
		location: string;
	} | null = null;

	// Props
	export let initialLodging: any = null;
	export let currentUser: any = null;
	export let editingLodging: any = null;
	export let collection: Collection | null = null;

	// Form data
	let lodging: {
		name: string;
		type: string;
		description: string;
		link: string;
		reservation_number: string | null;
		latitude: number | null;
		longitude: number | null;
		location: string;
		collections?: string[];
		is_public?: boolean;
		tags?: string[];
	} = {
		name: '',
		type: '',
		description: '',
		link: '',
		reservation_number: null,
		latitude: null,
		longitude: null,
		location: '',
		collections: collection?.id ? [collection.id] : [],
		is_public: true,
		tags: []
	};

	let user: User | null = null;
	let lodgingToEdit: Lodging | null = null;

	$: user = currentUser;
	$: lodgingToEdit = editingLodging;
	$: initialSelection =
		initialLodging && initialLodging.latitude && initialLodging.longitude
			? {
					name: initialLodging.name || '',
					lat: Number(initialLodging.latitude),
					lng: Number(initialLodging.longitude),
					location: initialLodging.location || ''
				}
			: null;

	function handleLocationUpdate(
		event: CustomEvent<{ name?: string; lat: number; lng: number; location: string }>
	) {
		const { name, lat, lng, location } = event.detail;
		if (!lodging.name && name) lodging.name = name;
		lodging.latitude = lat;
		lodging.longitude = lng;
		lodging.location = location;
	}

	function handleLocationClear() {
		lodging.latitude = null;
		lodging.longitude = null;
		lodging.location = '';
	}

	async function handleSave() {
		if (!lodging.name || !lodging.type) return;

		if (lodging.latitude !== null && typeof lodging.latitude === 'number') {
			lodging.latitude = parseFloat(lodging.latitude.toFixed(6));
		}
		if (lodging.longitude !== null && typeof lodging.longitude === 'number') {
			lodging.longitude = parseFloat(lodging.longitude.toFixed(6));
		}
		if (collection && collection.id) {
			if (!lodging.collections || lodging.collections.length === 0) {
				lodging.collections = [collection.id];
			} else if (!lodging.collections.includes(collection.id)) {
				lodging.collections = [...lodging.collections, collection.id];
			}
		}

		let payload: any = { ...lodging };

		if (!payload.link || payload.link.trim() === '') {
			delete payload.link;
		}

		if (lodgingToEdit && lodgingToEdit.id) {
			if (
				(!payload.collections || payload.collections.length === 0) &&
				lodgingToEdit.collections &&
				lodgingToEdit.collections.length > 0
			) {
				delete payload.collections;
			}

			const res = await fetch(`/api/lodging/${lodgingToEdit.id}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload)
			});
			lodging = await res.json();
		} else {
			const res = await fetch(`/api/lodging`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload)
			});
			lodging = await res.json();
		}

		dispatch('save', { ...lodging });
	}

	function handleBack() {
		dispatch('back');
	}

	onMount(() => {
		// Fetch entity types from API
		fetchEntityTypes();

		if (initialLodging && initialLodging.latitude && initialLodging.longitude) {
			lodging.latitude = initialLodging.latitude;
			lodging.longitude = initialLodging.longitude;
			if (!lodging.name) lodging.name = initialLodging.name || '';
			if (initialLodging.location) lodging.location = initialLodging.location;
		}

		if (initialLodging && typeof initialLodging === 'object') {
			lodging.name = initialLodging.name || '';
			lodging.type = initialLodging.type || '';
			lodging.link = initialLodging.link || '';
			lodging.description = initialLodging.description || '';
			lodging.is_public = initialLodging.is_public ?? true;
			lodging.reservation_number = initialLodging.reservation_number || null;

			if (initialLodging.location) {
				lodging.location = initialLodging.location;
			}

			if (initialLodging.tags && Array.isArray(initialLodging.tags)) {
				lodging.tags = initialLodging.tags;
			}
		}
	});
</script>

<EntityDetailsBase
	bind:name={lodging.name}
	bind:description={lodging.description}
	bind:link={lodging.link}
	bind:is_public={lodging.is_public}
	bind:tags={lodging.tags}
	namePlaceholder={$t('lodging.enter_lodging_name')}
	linkPlaceholder={$t('lodging.enter_link')}
	publicLabel={$t('lodging.public_lodging')}
	publicDescription={$t('lodging.public_lodging_description')}
	entityNameForGenerate={lodging.name}
	descriptionDisabled={!lodging.type}
	isProcessing={isReverseGeocoding}
	disabled={!lodging.name || !lodging.type || isReverseGeocoding}
	on:save={handleSave}
	on:back={handleBack}
>
	<svelte:fragment slot="type-field">
		<!-- Type Field -->
		<div class="form-control">
			<label class="label" for="type">
				<span class="label-text font-medium">
					{$t('lodging.type')} <span class="text-error">*</span>
				</span>
			</label>
			<select
				class="select select-bordered w-full bg-base-100/80 focus:bg-base-100"
				name="type"
				id="type"
				required
				bind:value={lodging.type}
			>
				<option disabled value="">{$t('lodging.select_type')}</option>
				{#if $lodgingTypes.length > 0}
					{#each $lodgingTypes as type}
						<option value={type.key}>{type.icon} {type.name}</option>
					{/each}
				{:else}
					<option value="hotel">🏨 {$t('lodging.hotel')}</option>
					<option value="hostel">🛏️ {$t('lodging.hostel')}</option>
					<option value="resort">🏝️ {$t('lodging.resort')}</option>
					<option value="bnb">🍳 {$t('lodging.bnb')}</option>
					<option value="campground">🏕️ {$t('lodging.campground')}</option>
					<option value="cabin">🏚️ {$t('lodging.cabin')}</option>
					<option value="apartment">🏢 {$t('lodging.apartment')}</option>
					<option value="house">🏠 {$t('lodging.house')}</option>
					<option value="villa">🏡 {$t('lodging.villa')}</option>
					<option value="motel">🚗🏨 {$t('lodging.motel')}</option>
					<option value="other">❓ {$t('lodging.other')}</option>
				{/if}
			</select>
		</div>
	</svelte:fragment>

	<svelte:fragment slot="left-extra">
		<!-- Reservation Number -->
		<div class="form-control">
			<label class="label" for="reservation">
				<span class="label-text font-medium">{$t('lodging.reservation_number')}</span>
			</label>
			<input
				type="text"
				id="reservation"
				bind:value={lodging.reservation_number}
				class="input input-bordered bg-base-100/80 focus:bg-base-100"
				placeholder={$t('lodging.enter_reservation_number')}
			/>
		</div>
	</svelte:fragment>

	<svelte:fragment slot="map">
		<LocationSearchMap
			{initialSelection}
			bind:isReverseGeocoding
			bind:displayName={lodging.location}
			displayNamePosition="before"
			on:update={handleLocationUpdate}
			on:clear={handleLocationClear}
		/>
	</svelte:fragment>
</EntityDetailsBase>
