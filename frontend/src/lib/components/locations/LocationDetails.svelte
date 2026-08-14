<script lang="ts">
	import { run } from 'svelte/legacy';

	import { createEventDispatcher, onMount } from 'svelte';
	import { t, locale } from 'svelte-i18n';
	import CategoryDropdown from '../CategoryDropdown.svelte';
	import LocationSearchMap from '../shared/LocationSearchMap.svelte';
	import MoneyInput from '../shared/MoneyInput.svelte';
	import MarkdownEditor from '../MarkdownEditor.svelte';
	import TagComplete from '../TagComplete.svelte';
	import { DEFAULT_CURRENCY, toMoneyValue } from '$lib/money';
	import { normalizeBasemapType } from '$lib';
	import { saveLocation } from '$lib/location-save';
	import { addToast } from '$lib/toasts';
	import type { Category, Collection, Location, MoneyValue, User } from '$lib/types';
	import MapIcon from '~icons/mdi/map';
	import InfoIcon from '~icons/mdi/information';
	import CategoryIcon from '~icons/mdi/tag';
	import ArrowLeftIcon from '~icons/mdi/arrow-left';
	import SaveIcon from '~icons/mdi/content-save';
	import ClearIcon from '~icons/mdi/close-circle';

	const dispatch = createEventDispatcher();

	let isReverseGeocoding = $state(false);
	let defaultCurrency = $state(DEFAULT_CURRENCY);
	let moneyValue: MoneyValue = $state({ amount: null, currency: DEFAULT_CURRENCY });

	let initialSelection: {
		name: string;
		lat: number;
		lng: number;
		location: string;
		category?: any;
	} | null = $state(null);

	let location: {
		name: string;
		category: Category | null;
		rating: number;
		price: number | null;
		price_currency: string | null;
		is_public: boolean;
		link: string;
		description: string;
		latitude: number | null;
		longitude: number | null;
		location: string;
		tags: string[];
		collections?: string[];
	} = $state({
		name: '',
		category: null,
		rating: NaN,
		price: null,
		price_currency: DEFAULT_CURRENCY,
		is_public: false,
		link: '',
		description: '',
		latitude: null,
		longitude: null,
		location: '',
		tags: [],
		collections: []
	});

	let user: User | null = $state(null);
	let locationToEdit: Location | null = $state(null);
	let ownerUser: User | null = $state(null);

	function toFiniteNumber(value: unknown): number | null {
		if (value === null || value === undefined) {
			return null;
		}
		const parsed = Number(value);
		return Number.isFinite(parsed) ? parsed : null;
	}

	interface Props {
		initialLocation?: any;
		currentUser?: any;
		editingLocation?: any;
		collection?: Collection | null;
	}

	let {
		initialLocation = null,
		currentUser = null,
		editingLocation = $bindable(null),
		collection = null
	}: Props = $props();

	run(() => {
		user = currentUser;
	});
	run(() => {
		locationToEdit = editingLocation;
	});
	run(() => {
		defaultCurrency = (user && user.default_currency) || DEFAULT_CURRENCY;
	});
	run(() => {
		moneyValue =
			location.price === null
				? { amount: null, currency: location.price_currency || defaultCurrency }
				: toMoneyValue(location.price, location.price_currency, defaultCurrency);
	});
	run(() => {
		if (location.price !== null && !location.price_currency) {
			location.price_currency = defaultCurrency;
		}
	});
	run(() => {
		const lat = toFiniteNumber(initialLocation?.latitude);
		const lng = toFiniteNumber(initialLocation?.longitude);
		initialSelection =
			initialLocation && lat !== null && lng !== null
				? {
						name: initialLocation.name || '',
						lat,
						lng,
						location: initialLocation.location || ''
					}
				: null;
	});

	function handleLocationUpdate(
		event: CustomEvent<{ name?: string; lat: number; lng: number; location: string }>
	) {
		const { name, lat, lng, location: displayName } = event.detail;
		if (name) location.name = name;
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
		if (!location.name || !location.category) {
			addToast('warning', 'Name and category are required');
			return;
		}

		try {
			const savedLocation = await saveLocation({
				location,
				locationToEdit,
				collectionId: collection?.id || null,
				defaultCurrency
			});
			location = {
				...location,
				...savedLocation,
				rating:
					typeof savedLocation.rating === 'number' && !Number.isNaN(savedLocation.rating)
						? savedLocation.rating
						: location.rating,
				link: savedLocation.link || location.link || '',
				description: savedLocation.description || location.description || '',
				location: savedLocation.location || location.location || '',
				tags: savedLocation.tags || location.tags || [],
				collections: savedLocation.collections || location.collections || []
			};
		} catch (error) {
			addToast('error', error instanceof Error ? error.message : 'Failed to save location');
			return;
		}

		dispatch('save', {
			...location
		});
	}

	function handleBack() {
		dispatch('back');
	}

	onMount(() => {
		const lat = toFiniteNumber(initialLocation?.latitude);
		const lng = toFiniteNumber(initialLocation?.longitude);
		if (initialLocation && lat !== null && lng !== null) {
			location.latitude = lat;
			location.longitude = lng;
			if (!location.name) location.name = initialLocation.name || '';
			if (initialLocation.location) location.location = initialLocation.location;
		}
	});

	onMount(() => {
		if (initialLocation && typeof initialLocation === 'object') {
			if (!location.name) location.name = initialLocation.name || '';
			if (!location.link) location.link = initialLocation.link || '';
			if (!location.description) location.description = initialLocation.description || '';
			if (Number.isNaN(location.rating)) location.rating = initialLocation.rating || NaN;
			if (location.price === null || location.price === undefined) {
				const money = toMoneyValue(
					initialLocation.price,
					initialLocation.price_currency,
					defaultCurrency
				);
				location.price = money.amount;
				location.price_currency = money.currency;
			}
			if (location.is_public === false) location.is_public = initialLocation.is_public || false;

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

		return () => {
			// no-op
		};
	});
</script>

<div class="h-full min-h-0 flex flex-col">
	<div class="flex-1 min-h-0 overflow-y-auto px-4 md:px-6 py-4 md:py-5 space-y-6">
		<!-- Basic Information Section -->
		<div class="card bg-base-100 border border-base-300">
			<div class="card-body p-6">
				<div class="flex items-center gap-3 mb-6">
					<div class="p-2 bg-primary/10 rounded-lg">
						<InfoIcon class="w-5 h-5 text-primary" />
					</div>
					<h2 class="text-xl font-bold text-base-content">{$t('adventures.basic_information')}</h2>
				</div>

				<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
					<!-- Left Column -->
					<div class="space-y-4">
						<!-- Name Field -->
						<div class="flex flex-col">
							<label class="field-label" for="name">
								{$t('adventures.name')} <span class="text-error">*</span>
							</label>
							<input
								type="text"
								id="name"
								bind:value={location.name}
								class="input w-full"
								placeholder="Enter location name"
								required
							/>
						</div>

						<!-- Category Field -->
						<div class="flex flex-col">
							<label class="field-label" for="category">
								{$t('adventures.category')} <span class="text-error">*</span>
							</label>
							{#if (user && ownerUser && user.uuid == ownerUser.uuid) || !ownerUser}
								<CategoryDropdown id="category" bind:selected_category={location.category} />
							{:else}
								<div
									class="flex items-center gap-3 p-3 bg-base-200/40 border border-base-300 rounded-lg"
								>
									{#if location.category?.icon}
										<span class="text-xl shrink-0">{location.category.icon}</span>
									{/if}
									<span class="font-medium">
										{location.category?.display_name || location.category?.name}
									</span>
								</div>
							{/if}
						</div>

						<MoneyInput
							label={$t('adventures.price')}
							value={moneyValue}
							{defaultCurrency}
							on:change={(event) => {
								location.price = event.detail.amount;
								location.price_currency = event.detail.currency || defaultCurrency;
							}}
						/>

						<!-- Rating Field -->
						<div class="flex flex-col">
							<label class="field-label" for="rating">{$t('adventures.rating')}</label>
							<div
								class="flex items-center gap-4 p-3 bg-base-200/40 border border-base-300 rounded-lg"
							>
								<div class="rating">
									<input
										type="radio"
										name="rating"
										id="rating"
										class="rating-hidden"
										checked={Number.isNaN(location.rating)}
									/>
									{#each [1, 2, 3, 4, 5] as star}
										<input
											type="radio"
											name="rating"
											class="mask mask-star-2 bg-warning"
											onclick={() => (location.rating = star)}
											checked={location.rating === star}
										/>
									{/each}
								</div>
								{#if !Number.isNaN(location.rating)}
									<button
										type="button"
										class="btn btn-sm btn-error btn-outline gap-2"
										onclick={() => (location.rating = NaN)}
									>
										<ClearIcon class="w-4 h-4" />
										{$t('adventures.remove')}
									</button>
								{/if}
							</div>
						</div>
					</div>

					<!-- Right Column -->
					<div class="space-y-4">
						<!-- Link Field -->
						<div class="flex flex-col">
							<label class="field-label" for="link">{$t('adventures.link')}</label>
							<input
								type="url"
								id="link"
								bind:value={location.link}
								class="input w-full"
								placeholder="https://example.com"
							/>
						</div>

						<!-- Public Toggle -->
						{#if !locationToEdit || (locationToEdit.collections && locationToEdit.collections.length === 0)}
							<div class="flex flex-col">
								<label class="field-toggle" for="is_public">
									<input
										type="checkbox"
										class="toggle toggle-primary"
										id="is_public"
										bind:checked={location.is_public}
									/>
									<span>
										<span class="font-semibold text-base-content">{$t('adventures.public_location')}</span>
										<p class="field-hint">
											{$t('adventures.public_location_description')}
										</p>
									</span>
								</label>
							</div>
						{/if}

						<!-- Description Field -->
						<div class="flex flex-col">
							<label class="field-label" for="description">{$t('adventures.description')}</label>
							<MarkdownEditor
								id="description"
								bind:text={location.description}
								editor_height="h-32"
								enableFetch
								fetchName={location.name}
								fetchLang={$locale || 'en'}
							/>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Tags Section -->
		<div class="card bg-base-100 border border-base-300">
			<div class="card-body p-6">
				<div class="flex items-center gap-3 mb-6">
					<div class="p-2 bg-warning/10 rounded-lg">
						<CategoryIcon class="w-5 h-5 text-warning" />
					</div>
					<h2 class="text-xl font-bold">{$t('adventures.tags')} ({location.tags?.length || 0})</h2>
				</div>
				<div class="space-y-4">
					<input
						type="text"
						id="tags"
						name="tags"
						hidden
						bind:value={location.tags}
						class="input w-full"
					/>
					<TagComplete bind:tags={location.tags} />
				</div>
			</div>
		</div>

		<!-- Location Selection Section -->
		<div class="card bg-base-100 border border-base-300">
			<div class="card-body p-6">
				<div class="flex items-center gap-3 mb-6">
					<div class="p-2 bg-secondary/10 rounded-lg">
						<MapIcon class="w-5 h-5 text-secondary" />
					</div>
					<h2 class="text-xl font-bold">{$t('adventures.location_map')}</h2>
				</div>

				<LocationSearchMap
					{initialSelection}
					bind:isReverseGeocoding
					bind:displayName={location.location}
					basemapType={normalizeBasemapType(user?.map_style)}
					displayNamePosition="before"
					on:update={handleLocationUpdate}
					on:clear={handleLocationClear}
				/>
			</div>
		</div>

	</div>

		<!-- Action Buttons -->
		<div
			class="shrink-0 border-t border-base-300 bg-base-100/90 backdrop-blur-lg px-4 md:px-6 py-3 md:py-4 flex gap-3 justify-end"
		>
			<button class="btn btn-ghost gap-2" onclick={handleBack}>
				<ArrowLeftIcon class="w-5 h-5" />
				{$t('adventures.back')}
			</button>
			<button
				class="btn btn-primary gap-2"
				disabled={!location.name || !location.category || isReverseGeocoding}
				onclick={handleSave}
			>
				{#if isReverseGeocoding}
					<span class="loading loading-spinner loading-sm"></span>
					{$t('adventures.processing')}...
				{:else}
					<SaveIcon class="w-5 h-5" />
					{$t('adventures.continue')}
				{/if}
			</button>
		</div>
</div>
