<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { t, locale } from 'svelte-i18n';
	import CategoryDropdown from '../CategoryDropdown.svelte';
	import LocationSearchMap from '../shared/LocationSearchMap.svelte';
	import MoneyInput from '../shared/MoneyInput.svelte';
	import MarkdownEditor from '../MarkdownEditor.svelte';
	import TagComplete from '../TagComplete.svelte';
	import { DEFAULT_CURRENCY, normalizeMoneyPayload, toMoneyValue } from '$lib/money';
	import { addToast } from '$lib/toasts';
	import type { Category, Collection, Location, MoneyValue, User } from '$lib/types';
	import MapIcon from '~icons/mdi/map';
	import InfoIcon from '~icons/mdi/information';
	import CategoryIcon from '~icons/mdi/tag';
	import GenerateIcon from '~icons/mdi/lightning-bolt';
	import ArrowLeftIcon from '~icons/mdi/arrow-left';
	import SaveIcon from '~icons/mdi/content-save';
	import ClearIcon from '~icons/mdi/close-circle';

	const dispatch = createEventDispatcher();

	let isReverseGeocoding = false;
	let defaultCurrency = DEFAULT_CURRENCY;
	let moneyValue: MoneyValue = { amount: null, currency: DEFAULT_CURRENCY };

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
	} = {
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
	};

	let user: User | null = null;
	let locationToEdit: Location | null = null;
	let wikiError = '';
	let isGeneratingDesc = false;
	let ownerUser: User | null = null;

	export let initialLocation: any = null;
	export let currentUser: any = null;
	export let editingLocation: any = null;
	export let collection: Collection | null = null;

	$: user = currentUser;
	$: locationToEdit = editingLocation;
	$: defaultCurrency = (user && user.default_currency) || DEFAULT_CURRENCY;
	$: moneyValue =
		location.price === null
			? { amount: null, currency: location.price_currency || null }
			: toMoneyValue(location.price, location.price_currency, defaultCurrency);
	$: {
		if (location.price !== null && !location.price_currency) {
			location.price_currency = defaultCurrency;
		}
	}
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

	async function generateDesc() {
		if (!location.name) return;

		isGeneratingDesc = true;
		wikiError = '';

		try {
			const response = await fetch(
				`/api/generate/desc/?name=${encodeURIComponent(location.name)}&lang=${$locale || 'en'}`
			);
			if (response.ok) {
				const data = await response.json();
				location.description = data.extract || '';
			} else {
				wikiError = `${$t('adventures.wikipedia_error') || 'Error fetching description from Wikipedia'}`;
			}
		} catch (error) {
			wikiError = `${$t('adventures.wikipedia_error') || ''}`;
		} finally {
			isGeneratingDesc = false;
		}
	}

	async function handleSave() {
		if (!location.name || !location.category) {
			addToast('warning', 'Name and category are required');
			return;
		}

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

		// Clean up link: empty/whitespace → null, invalid URL → null
		if (!payload.link || !payload.link.trim()) {
			payload.link = null;
		} else {
			try {
				new URL(payload.link);
			} catch {
				// Not a valid URL — clear it so Django doesn't reject it
				payload.link = null;
			}
		}
		if (!payload.description || !payload.description.trim()) {
			payload.description = null;
		}

		if (location.price === null) {
			payload.price = null;
			payload.price_currency = null;
		} else {
			payload = normalizeMoneyPayload(payload, 'price', 'price_currency', defaultCurrency);
		}

		let res: Response;
		if (locationToEdit && locationToEdit.id) {
			// Only include collections if explicitly set via a collection context;
			// otherwise remove them from the PATCH payload to avoid triggering the
			// m2m_changed signal which can override is_public.
			if (!collection || !collection.id) {
				delete payload.collections;
			}

			res = await fetch(`/api/locations/${locationToEdit.id}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(payload)
			});
		} else {
			res = await fetch(`/api/locations`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(payload)
			});
		}

		if (!res.ok) {
			const errorData = await res.json().catch(() => ({}));
			// Extract error message from Django field errors (e.g. {"link": ["Enter a valid URL."]})
			let errorMsg = errorData?.detail || errorData?.name?.[0] || '';
			if (!errorMsg) {
				const fieldErrors = Object.entries(errorData)
					.filter(([_, v]) => Array.isArray(v))
					.map(([k, v]) => `${k}: ${(v as string[]).join(', ')}`)
					.join('; ');
				errorMsg = fieldErrors || 'Failed to save location';
			}
			addToast('error', String(errorMsg));
			return;
		}

		location = await res.json();

		dispatch('save', {
			...location
		});
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

<div class="min-h-screen bg-gradient-to-br from-base-200/30 via-base-100 to-primary/5 p-6">
	<div class="max-w-full mx-auto space-y-6">
		<!-- Basic Information Section -->
		<div class="card bg-base-100 border border-base-300 shadow-lg">
			<div class="card-body p-6">
				<div class="flex items-center gap-3 mb-6">
					<div class="p-2 bg-primary/10 rounded-lg">
						<InfoIcon class="w-5 h-5 text-primary" />
					</div>
					<h2 class="text-xl font-bold">{$t('adventures.basic_information')}</h2>
				</div>

				<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
					<!-- Left Column -->
					<div class="space-y-4">
						<!-- Name Field -->
						<div class="form-control">
							<label class="label" for="name">
								<span class="label-text font-medium">
									{$t('adventures.name')} <span class="text-error">*</span>
								</span>
							</label>
							<input
								type="text"
								id="name"
								bind:value={location.name}
								class="input input-bordered bg-base-100/80 focus:bg-base-100"
								placeholder="Enter location name"
								required
							/>
						</div>

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
								<div
									class="flex items-center gap-3 p-3 bg-base-100/80 border border-base-300 rounded-lg"
								>
									{#if location.category?.icon}
										<span class="text-xl flex-shrink-0">{location.category.icon}</span>
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
							on:change={(event) => {
								location.price = event.detail.amount;
								location.price_currency = event.detail.currency;

								// If an amount exists but no currency is chosen, fall back to the user's default
								if (location.price !== null && !location.price_currency) {
									location.price_currency = defaultCurrency;
								}
							}}
						/>

						<!-- Rating Field -->
						<div class="form-control">
							<label class="label" for="rating">
								<span class="label-text font-medium">{$t('adventures.rating')}</span>
							</label>
							<div
								class="flex items-center gap-4 p-3 bg-base-100/80 border border-base-300 rounded-lg"
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
											on:click={() => (location.rating = star)}
											checked={location.rating === star}
										/>
									{/each}
								</div>
								{#if !Number.isNaN(location.rating)}
									<button
										type="button"
										class="btn btn-sm btn-error btn-outline gap-2"
										on:click={() => (location.rating = NaN)}
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
						<div class="form-control">
							<label class="label" for="link">
								<span class="label-text font-medium">{$t('adventures.link')}</span>
							</label>
							<input
								type="url"
								id="link"
								bind:value={location.link}
								class="input input-bordered bg-base-100/80 focus:bg-base-100"
								placeholder="https://example.com"
							/>
						</div>

						<!-- Public Toggle -->
						{#if !locationToEdit || (locationToEdit.collections && locationToEdit.collections.length === 0)}
							<div class="form-control">
								<label class="label cursor-pointer justify-start gap-4" for="is_public">
									<input
										type="checkbox"
										class="toggle toggle-primary"
										id="is_public"
										bind:checked={location.is_public}
									/>
									<div>
										<span class="label-text font-medium">{$t('adventures.public_location')}</span>
										<p class="text-sm text-base-content/60">
											{$t('adventures.public_location_description')}
										</p>
									</div>
								</label>
							</div>
						{/if}

						<!-- Description Field -->
						<div class="form-control">
							<label class="label" for="description">
								<span class="label-text font-medium">{$t('adventures.description')}</span>
							</label>
							<MarkdownEditor bind:text={location.description} editor_height="h-32" />

							<div class="flex items-center gap-4 mt-3">
								<button
									type="button"
									class="btn btn-neutral btn-sm gap-2"
									on:click={generateDesc}
									disabled={!location.name || isGeneratingDesc}
								>
									{#if isGeneratingDesc}
										<span class="loading loading-spinner loading-xs"></span>
									{:else}
										<GenerateIcon class="w-4 h-4" />
									{/if}
									{$t('adventures.generate_desc')}
								</button>
								{#if wikiError}
									<div class="alert alert-error alert-sm">
										<InfoIcon class="w-4 h-4" />
										<span class="text-sm">{wikiError}</span>
									</div>
								{/if}
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Tags Section -->
		<div class="card bg-base-100 border border-base-300 shadow-lg">
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
						class="input input-bordered w-full"
					/>
					<TagComplete bind:tags={location.tags} />
				</div>
			</div>
		</div>

		<!-- Location Selection Section -->
		<div class="card bg-base-100 border border-base-300 shadow-lg">
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
					displayNamePosition="before"
					on:update={handleLocationUpdate}
					on:clear={handleLocationClear}
				/>
			</div>
		</div>

		<!-- Action Buttons -->
		<div class="flex gap-3 justify-end pt-4">
			<button class="btn btn-neutral-200 gap-2" on:click={handleBack}>
				<ArrowLeftIcon class="w-5 h-5" />
				{$t('adventures.back')}
			</button>
			<button
				class="btn btn-primary gap-2"
				disabled={!location.name || !location.category || isReverseGeocoding}
				on:click={handleSave}
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
</div>
