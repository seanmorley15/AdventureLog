<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import CategoryDropdown from '../CategoryDropdown.svelte';
	import LocationSearchMap from '../shared/LocationSearchMap.svelte';
	import { EntityDetailsBase } from '../shared/modal';
	import type { Category, Collection, Location, User } from '$lib/types';

	const dispatch = createEventDispatcher();

	let isReverseGeocoding = false;

	let initialSelection: {
		name: string;
		lat: number;
		lng: number;
		location: string;
		category?: any;
	} | null = null;

	let location: {
		name: string;
		category: Category | null;
		is_public: boolean;
		link: string;
		description: string;
		latitude: number | null;
		longitude: number | null;
		location: string;
		tags: string[];
		collections?: string[];
	} = {
		name: '',
		category: null,
		is_public: true,
		link: '',
		description: '',
		latitude: null,
		longitude: null,
		location: '',
		tags: [],
		collections: []
	};

	let user: User | null = null;
	let locationToEdit: Location | null = null;
	let ownerUser: User | null = null;

	export let initialLocation: any = null;
	export let currentUser: any = null;
	export let editingLocation: any = null;
	export let collection: Collection | null = null;

	$: user = currentUser;
	$: locationToEdit = editingLocation;
	$: initialSelection =
		initialLocation && initialLocation.latitude && initialLocation.longitude
			? {
					name: initialLocation.name || '',
					lat: Number(initialLocation.latitude),
					lng: Number(initialLocation.longitude),
					location: initialLocation.location || ''
				}
			: null;

	function handleLocationUpdate(
		event: CustomEvent<{ name?: string; lat: number; lng: number; location: string }>
	) {
		const { name, lat, lng, location: displayName } = event.detail;
		if (!location.name && name) location.name = name;
		location.latitude = lat;
		location.longitude = lng;
		location.location = displayName;
	}

	function handleLocationClear() {
		location.latitude = null;
		location.longitude = null;
		location.location = '';
	}

	async function handleSave() {
		if (!location.name || !location.category) return;

		if (location.latitude !== null && typeof location.latitude === 'number') {
			location.latitude = parseFloat(location.latitude.toFixed(6));
		}
		if (location.longitude !== null && typeof location.longitude === 'number') {
			location.longitude = parseFloat(location.longitude.toFixed(6));
		}
		if (collection && collection.id) {
			location.collections = [collection.id];
		}

		let payload: any = { ...location };

		if (locationToEdit && locationToEdit.id) {
			if (
				(!payload.collections || payload.collections.length === 0) &&
				locationToEdit.collections &&
				locationToEdit.collections.length > 0
			) {
				delete payload.collections;
			}

			const res = await fetch(`/api/locations/${locationToEdit.id}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload)
			});
			location = await res.json();
		} else {
			const res = await fetch(`/api/locations`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload)
			});
			location = await res.json();
		}

		dispatch('save', { ...location });
	}

	function handleBack() {
		dispatch('back');
	}

	onMount(() => {
		if (initialLocation && initialLocation.latitude && initialLocation.longitude) {
			location.latitude = initialLocation.latitude;
			location.longitude = initialLocation.longitude;
			if (!location.name) location.name = initialLocation.name || '';
			if (initialLocation.location) location.location = initialLocation.location;
		}

		if (initialLocation && typeof initialLocation === 'object') {
			if (!location.name) location.name = initialLocation.name || '';
			if (!location.link) location.link = initialLocation.link || '';
			if (!location.description) location.description = initialLocation.description || '';
			if (location.is_public === false) location.is_public = initialLocation.is_public ?? true;

			if (!location.category || !location.category.id) {
				if (initialLocation.category && initialLocation.category.id) {
					location.category = initialLocation.category;
				}
			}

			if (initialLocation.tags && Array.isArray(initialLocation.tags)) {
				location.tags = initialLocation.tags;
			}

			if (initialLocation.collections && Array.isArray(initialLocation.collections)) {
				location.collections = initialLocation.collections.map((c: any) =>
					typeof c === 'string' ? c : c.id
				);
			} else if (
				locationToEdit &&
				locationToEdit.collections &&
				Array.isArray(locationToEdit.collections)
			) {
				location.collections = locationToEdit.collections.map((c: any) =>
					typeof c === 'string' ? c : c.id
				);
			}

			if (initialLocation.location) {
				location.location = initialLocation.location;
			}

			if (initialLocation.user) {
				ownerUser = initialLocation.user;
			}
		}
	});
</script>

<EntityDetailsBase
	bind:name={location.name}
	bind:description={location.description}
	bind:link={location.link}
	bind:is_public={location.is_public}
	bind:tags={location.tags}
	namePlaceholder="Enter location name"
	publicLabel={$t('adventures.public_location')}
	publicDescription={$t('adventures.public_location_description')}
	entityNameForGenerate={location.name}
	isProcessing={isReverseGeocoding}
	disabled={!location.name || !location.category || isReverseGeocoding}
	on:save={handleSave}
	on:back={handleBack}
>
	<svelte:fragment slot="type-field">
		<!-- Category Field -->
		<div class="form-control">
			<label class="label" for="category">
				<span class="label-text font-medium">
					{$t('adventures.category')} <span class="text-error">*</span>
				</span>
			</label>
			{#if (user && ownerUser && user.uuid == ownerUser.uuid) || !ownerUser}
				<CategoryDropdown bind:selected_category={location.category} />
			{:else}
				<div class="flex items-center gap-3 p-3 bg-base-100/80 border border-base-300 rounded-lg">
					{#if location.category?.icon}
						<span class="text-xl flex-shrink-0">{location.category.icon}</span>
					{/if}
					<span class="font-medium">
						{location.category?.display_name || location.category?.name}
					</span>
				</div>
			{/if}
		</div>
	</svelte:fragment>

	<svelte:fragment slot="map">
		<LocationSearchMap
			{initialSelection}
			bind:isReverseGeocoding
			bind:displayName={location.location}
			displayNamePosition="before"
			on:update={handleLocationUpdate}
			on:clear={handleLocationClear}
		/>
	</svelte:fragment>
</EntityDetailsBase>
